# Experiment 001 Operations

## Runtime boundary

Generated Python executes only inside the locked Docker runner:

- no network
- read-only root filesystem
- repository mounted read-only
- only `~/.local/state/sovereign-colony` mounted writable
- all Linux capabilities dropped
- `no-new-privileges`
- 256 MiB memory, 0.5 CPU, 64 PID ceiling
- non-root host UID/GID

The trusted host mediator invokes local Ollama separately. A citizen receives only its public prompt and returns inert JSON. Responses are never evaluated or used as commands. The Docker kernel validates every response against `CitizenDecision/v1` before any state mutation. A missing or invalid response aborts the entire day.

## Operator commands

These examples use the same sandbox boundary as the hourly runner.

```bash
STATE="$HOME/.local/state/sovereign-colony"
PROJECT="$HOME/Projects/sovereign-colony"

# Status
bash "$PROJECT/scripts/colony_operator.sh" status

# Stop autonomous time immediately
bash "$PROJECT/scripts/colony_operator.sh" pause

# Resume hourly turns
bash "$PROJECT/scripts/colony_operator.sh" resume

# Emergency stop with an immutable audit event
bash "$PROJECT/scripts/colony_operator.sh" emergency-pause "reason"
```

## Runtime files

- Database: `~/.local/state/sovereign-colony/experiment-001.db`
- Per-day model batches: `~/.local/state/sovereign-colony/batches/day-NNN/`
- Day report: `day-NNN/day-report.json`
- Timer logs: `journalctl --user -u sovereign-colony.service`

The SQLite database and model responses are intentionally outside the public repository. Public artifacts remain pending until Creator review.
