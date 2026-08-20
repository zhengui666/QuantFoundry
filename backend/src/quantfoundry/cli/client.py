"""Loopback-only API client for the local qf CLI."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx


class CliClientError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def validate_loopback_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise CliClientError("endpoint must use http or https")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise CliClientError("REMOTE_API_ENDPOINT_FORBIDDEN")
    if parsed.username or parsed.password:
        raise CliClientError("credentials must not be embedded in the endpoint")
    return endpoint.rstrip("/")


class ApiClient:
    def __init__(self, endpoint: str, *, timeout_seconds: float = 10.0) -> None:
        self.endpoint = validate_loopback_endpoint(endpoint)
        self._client = httpx.Client(base_url=self.endpoint, timeout=timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ApiClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = self._client.request(method, path, json=json_body)
        except httpx.HTTPError as exc:
            raise CliClientError(f"API unavailable: {exc}") from exc
        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise CliClientError(
                f"API returned non-JSON response ({response.status_code})",
                status_code=response.status_code,
            ) from exc
        if response.is_error:
            message = payload
            if isinstance(payload, dict):
                error = payload.get("error")
                if isinstance(error, dict):
                    message = f"{error.get('code')}: {error.get('message')}"
            raise CliClientError(str(message), status_code=response.status_code)
        return payload
