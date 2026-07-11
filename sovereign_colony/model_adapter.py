from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Any

from .persistence import SQLiteColonyStore
from .turns import TurnEngine, TurnReport, build_citizen_prompt


class ModelAdapterError(RuntimeError):
    """Raised when mediated model input or output violates the adapter contract."""


def _ensure_real_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise ModelAdapterError(f"unsafe batch directory: {path}")
    return path.resolve()


def _atomic_text_write(path: Path, content: str) -> None:
    parent = _ensure_real_directory(path.parent)
    target = path.resolve(strict=False)
    if target.parent != parent or path.is_symlink():
        raise ModelAdapterError(f"unsafe output path: {path}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=parent,
            prefix=f".{path.name}.tmp-",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def prepare_prompt_batch(
    store: SQLiteColonyStore,
    batch_dir: str | Path,
    *,
    model: str,
) -> dict[str, Any]:
    if store.is_paused():
        raise ModelAdapterError("cannot prepare model prompts while colony is paused")
    if not model or len(model) > 120:
        raise ModelAdapterError("model identifier is invalid")

    world = store.load()
    root = _ensure_real_directory(Path(batch_dir))
    request_dir = _ensure_real_directory(root / "requests")
    citizens = [
        citizen.citizen_id
        for citizen in world.citizens.values()
        if citizen.alive
    ]
    manifest = {
        "experiment": world.config.name,
        "source_day": world.colony_day,
        "target_day": world.colony_day + 1,
        "source_state_digest": world.state_digest(),
        "source_ledger_tip": world.ledger.events[-1].event_digest,
        "model": model,
        "citizens": citizens,
        "response_contract": "CitizenDecision/v1",
    }
    for citizen_id in citizens:
        prompt = build_citizen_prompt(world, world.citizens[citizen_id])
        _atomic_text_write(request_dir / f"{citizen_id}.txt", prompt)
    _atomic_text_write(
        root / "manifest.json",
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    )
    return manifest


class FileDecisionProvider:
    MAX_RESPONSE_BYTES = 16_384

    def __init__(self, response_dir: str | Path) -> None:
        self.response_dir = Path(response_dir)

    def __call__(self, prompt: str, citizen_id: str) -> str:
        del prompt
        if not citizen_id or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in citizen_id):
            raise ModelAdapterError("citizen identifier is unsafe")
        if self.response_dir.is_symlink() or not self.response_dir.is_dir():
            raise ModelAdapterError("response directory is missing or unsafe")
        root = self.response_dir.resolve()
        path = self.response_dir / f"{citizen_id}.json"
        if path.is_symlink():
            raise ModelAdapterError(f"symlinked model response rejected: {citizen_id}")
        try:
            metadata = path.stat()
        except FileNotFoundError as exc:
            raise ModelAdapterError(f"missing model response: {citizen_id}") from exc
        if not stat.S_ISREG(metadata.st_mode) or path.resolve().parent != root:
            raise ModelAdapterError(f"unsafe model response: {citizen_id}")
        if metadata.st_size == 0 or metadata.st_size > self.MAX_RESPONSE_BYTES:
            raise ModelAdapterError(f"model response size rejected: {citizen_id}")
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ModelAdapterError(f"model response is not UTF-8: {citizen_id}") from exc
        if "\x00" in content:
            raise ModelAdapterError(f"model response contains NUL: {citizen_id}")
        return content.strip()


def _load_manifest(batch_dir: Path) -> dict[str, Any]:
    path = batch_dir / "manifest.json"
    if path.is_symlink() or not path.is_file():
        raise ModelAdapterError("batch manifest is missing or unsafe")
    if path.stat().st_size > 32_768:
        raise ModelAdapterError("batch manifest is oversized")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ModelAdapterError("batch manifest is invalid") from exc
    if not isinstance(manifest, dict):
        raise ModelAdapterError("batch manifest must be an object")
    required = {
        "experiment",
        "source_day",
        "target_day",
        "source_state_digest",
        "source_ledger_tip",
        "model",
        "citizens",
        "response_contract",
    }
    if set(manifest) != required:
        raise ModelAdapterError("batch manifest fields do not match contract")
    return manifest


def apply_response_batch(
    store: SQLiteColonyStore,
    batch_dir: str | Path,
) -> TurnReport:
    root = Path(batch_dir)
    if root.is_symlink() or not root.is_dir():
        raise ModelAdapterError("batch directory is missing or unsafe")
    manifest = _load_manifest(root)
    world = store.load()
    if manifest["experiment"] != world.config.name:
        raise ModelAdapterError("batch belongs to a different experiment")
    if manifest["source_day"] != world.colony_day or manifest["target_day"] != world.colony_day + 1:
        raise ModelAdapterError("batch day is stale or out of sequence")
    if manifest["source_state_digest"] != world.state_digest():
        raise ModelAdapterError("batch source state digest is stale")
    if manifest["source_ledger_tip"] != world.ledger.events[-1].event_digest:
        raise ModelAdapterError("batch ledger tip is stale")
    expected_citizens = [
        citizen.citizen_id for citizen in world.citizens.values() if citizen.alive
    ]
    if manifest["citizens"] != expected_citizens:
        raise ModelAdapterError("batch citizen roster is stale")
    if manifest["response_contract"] != "CitizenDecision/v1":
        raise ModelAdapterError("unsupported response contract")

    provider = FileDecisionProvider(root / "responses")
    engine = TurnEngine(store, provider)
    return engine.advance_one_day()
