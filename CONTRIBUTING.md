# Contributing to QuantFoundry

Thank you for helping improve QuantFoundry.

## Before you start

QuantFoundry is Paper-only and self-hosted. Read [PROJECT_BACKGROUND.md](PROJECT_BACKGROUND.md), [AGENTS.md](AGENTS.md), and the applicable document under `docs/` before proposing a change. Those documents are the source of truth for product behavior, contracts, architecture, and test requirements.

Do not implement a change that exceeds the documented boundary. Propose the documentation update first when your change affects a feature, field, API, workflow, permission, architecture, or acceptance gate.

## Local setup

You need Docker Compose, Python 3.14.0, Node 24.19.0, and pnpm 10.32.1.

```bash
make bootstrap
# Set local-only values in .env, including a new credential-encryption key.
make local-bootstrap
make up
```

Use `.env.example` as a template only. Never commit `.env`, real credentials, plaintext tokens, local artifacts, evidence, logs, or browser state. `frontend/e2e/storage-state.json` is ignored because Playwright/browser state can contain session material.

## Submit a change

1. Keep each pull request focused and explain the user-visible or governance impact.
2. Update applicable documentation before implementation when the documented contract changes.
3. Run the relevant checks locally. The project exposes `make format lint typecheck test build schema contract e2e visual` and `make verify-compose`; run the subset appropriate to your change.
4. Do not add generated build output, dependency directories, test reports, or release evidence to Git.
5. Use the pull-request template and respond to review feedback.

## Code of conduct and security

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report security vulnerabilities privately as described in [SECURITY.md](SECURITY.md); do not open a public issue for a suspected vulnerability.
