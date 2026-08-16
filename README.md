# QuantFoundry

> A self-hosted, Paper-only workbench for governed, agent-assisted quantitative research.

QuantFoundry keeps AI assistance inside a controlled research workflow: deterministic tools calculate official values, and research, validation, risk, approval, audit, and data-access rules cannot be bypassed by the agent or client. It does not support live-capital execution.

## Project status

This repository is preparing its first public baseline. `v0.1.0-alpha` is a release target, not a published release. The P0 registry currently contains open and blocked release gates, including Paper daily scheduler safety. Do not treat this repository as release-ready until every release-blocking P0 item has independent closure evidence.

See [P0 blockers](docs/%E6%B2%BB%E7%90%86/p0-blockers.yaml) and [repository governance](docs/%E6%B2%BB%E7%90%86/QuantFoundry_Repository_Governance_V1.0.0.md).

## Documentation

- [Project background and source-of-truth rules](PROJECT_BACKGROUND.md)
- [Product requirements](docs/PRD/V1.0.0.md)
- [Frontend technical design](docs/%E5%89%8D%E7%AB%AF%E6%8A%80%E6%9C%AF%E6%96%B9%E6%A1%88/QuantFoundry_Frontend_Technical_Design_V1.0.0.md)
- [Backend technical design](docs/%E5%90%8E%E7%AB%AF%E7%B3%BB%E7%BB%9F%E6%8A%80%E6%9C%AF%E6%96%B9%E6%A1%88/QuantFoundry_Backend_System_Technical_Design_V1.0.0.md)
- [Canonical OpenAPI contract](docs/%E5%90%8E%E7%AB%AF%E7%B3%BB%E7%BB%9F%E6%8A%80%E6%9C%AF%E6%96%B9%E6%A1%88/contracts/openapi-v1.yaml)
- [Agent technical design](docs/Agent%E6%8A%80%E6%9C%AF%E6%96%B9%E6%A1%88/QuantFoundry_Agent_Technical_Design_V1.0.0.md)
- [Full-stack test plan](docs/%E5%85%A8%E6%A0%88%E6%B5%8B%E8%AF%95%E6%96%B9%E6%A1%88/QuantFoundry_Full_Stack_Test_Plan_V1.0.0.md)

## Development

Prerequisites: Docker Compose, Python 3.14.0, Node 24.19.0, and pnpm 10.32.1.

```bash
make bootstrap
# Replace the local database password and generate the credential-encryption key.
make bootstrap
make owner-bootstrap
make up
```

The local edge is available at `http://localhost:8080`. `make owner-bootstrap` prints the only plaintext copy of the first general access key; use it once at `/login`, and do not save it to files, browser storage, logs, or commits.

Useful local checks:

```bash
make verify-compose
make format lint typecheck test build schema contract e2e visual
```

Use `.env.example` only as a non-secret starting point. Copy it to `.env`; never commit `.env`, credentials, evidence, artifacts, or Playwright/browser storage state. In particular, `frontend/e2e/storage-state.json` is local runtime state and is intentionally excluded even when it currently contains no authentication cookie.

## Distribution targets

The intended distribution is a public GitHub repository and GHCR container images. Neither a GHCR image nor a `v0.1.0-alpha` release has been published by this repository baseline. Release is permitted only after the governed P0 evidence requirements are met.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a change. Report vulnerabilities through [SECURITY.md](SECURITY.md), not public issues. Community expectations are in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

QuantFoundry is licensed under [AGPL-3.0-only](LICENSE). Third-party components remain under their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
