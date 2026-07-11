# Security Policy

## Current posture

The repository is specification-only. No autonomous execution is currently enabled.

## Security invariants

- Citizens are untrusted.
- The world is disposable.
- The kernel is minimal and externally governed.
- Network access is denied by default.
- Host secrets and user files are out of scope and inaccessible.
- Every consequential action is capability-gated, metered, and logged.
- Safety claims require adversarial tests and replay evidence.

## Reporting

Do not publish exploit details that could expose a running experiment or host. Open a private GitHub security advisory for boundary escapes, hidden-state paths, capability bypasses, accounting bypasses, digest-chain failures, or sandbox weaknesses.

## Not security boundaries

Agent prompts, social norms, voting, reputation, and citizen promises are not security controls. Enforcement belongs in the immutable kernel.
