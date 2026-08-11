SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

.PHONY: help bootstrap local-bootstrap owner-bootstrap up down logs ps migrate format lint typecheck test build e2e visual browser fresh-smoke schema contract openapi tools pg18 fullstack platform backend-ci frontend-ci ci governance p0-check release-check release-known-issues hygiene secrets licenses verify-compose

help:
	@echo "Targets: bootstrap local-bootstrap owner-bootstrap up down logs ps migrate format lint typecheck test build e2e visual browser fresh-smoke schema contract openapi tools pg18 fullstack platform backend-ci frontend-ci ci governance p0-check release-check release-known-issues hygiene secrets licenses verify-compose"

bootstrap:
	@./scripts/bootstrap.sh

owner-bootstrap:
	@./scripts/bootstrap-owner.sh

local-bootstrap:
	@./scripts/bootstrap-local.sh

up:
	@docker compose --profile local up --build --remove-orphans

down:
	@docker compose --profile local down --remove-orphans

logs:
	@docker compose --profile local logs --follow --tail=200

ps:
	@docker compose --profile local ps

migrate:
	@docker compose run --rm migrate

format lint typecheck test build e2e visual browser fresh-smoke schema contract openapi tools pg18 fullstack platform backend-ci frontend-ci ci governance p0-check release-check release-known-issues hygiene secrets licenses:
	@./scripts/ci.sh $@

verify-compose:
	@docker compose --env-file .env.example config --quiet
	@docker compose --profile local --env-file .env.example config --quiet
