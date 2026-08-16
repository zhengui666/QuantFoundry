"""FastAPI route class enforcing canonical request/parameter/response models."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import jsonschema
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from quantfoundry.contracts.openapi.api_models import validate_schema
from quantfoundry.contracts.openapi.runtime import (
    canonical_openapi,
    validate_json_schema,
)


def _resolve_parameter(parameter: dict[str, Any]) -> dict[str, Any]:
    if "$ref" not in parameter:
        return parameter
    name = parameter["$ref"].rsplit("/", 1)[-1]
    return canonical_openapi()["components"]["parameters"][name]


def _resolve_header(header: dict[str, Any]) -> dict[str, Any]:
    if "$ref" not in header:
        return header
    name = header["$ref"].rsplit("/", 1)[-1]
    return canonical_openapi()["components"]["headers"][name]


def _problem(request: Request, detail: str) -> JSONResponse:
    from quantfoundry.api.app import problem_payload

    return JSONResponse(
        problem_payload(500, "INTERNAL_ERROR", request, detail),
        status_code=500,
        media_type="application/problem+json",
    )


class CanonicalRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Any]:
        original = super().get_route_handler()
        path = self.path.removeprefix("/api/v1")

        async def handler(request: Request) -> Response:
            operation = (
                canonical_openapi()
                .get("paths", {})
                .get(path, {})
                .get(request.method.lower())
            )
            if operation is None:
                return await original(request)
            try:
                for raw_parameter in operation.get("parameters", []):
                    parameter = _resolve_parameter(raw_parameter)
                    location = parameter["in"]
                    name = parameter["name"]
                    if location == "path":
                        value = request.path_params.get(name)
                    elif location == "query":
                        value = request.query_params.get(name)
                    else:
                        value = request.headers.get(name)
                    if value is None:
                        if parameter.get("required"):
                            if location == "header" and name.lower() in {
                                "idempotency-key",
                                "if-match",
                            }:
                                continue
                            raise jsonschema.ValidationError(f"{name} is required")
                        continue
                    schema = parameter["schema"]
                    if schema.get("type") == "integer":
                        try:
                            value = int(value)
                        except (TypeError, ValueError) as error:
                            raise jsonschema.ValidationError(
                                f"{name} must be integer"
                            ) from error
                    validate_json_schema(schema, value)
                body_schema = (
                    operation.get("requestBody", {})
                    .get("content", {})
                    .get("application/json", {})
                    .get("schema", {})
                )
                reference = body_schema.get("$ref")
                if reference:
                    validate_schema(reference.rsplit("/", 1)[-1], await request.json())
            except (
                json.JSONDecodeError,
                jsonschema.ValidationError,
                ValueError,
            ) as error:
                from quantfoundry.api.app import invalid_request_response

                return invalid_request_response(request, error)

            response = await original(request)
            if (
                not 200 <= response.status_code < 300
                or response.media_type == "text/event-stream"
            ):
                return response
            declared = operation.get("responses", {}).get(str(response.status_code))
            if declared is None:
                return _problem(
                    request, "handler returned an undocumented success status"
                )
            for header_name, raw_header in declared.get("headers", {}).items():
                if header_name.lower() not in response.headers:
                    if not _resolve_header(raw_header).get("required", False):
                        continue
                    return _problem(
                        request, f"handler omitted required {header_name} header"
                    )
                try:
                    validate_json_schema(
                        _resolve_header(raw_header)["schema"],
                        response.headers[header_name],
                    )
                except jsonschema.ValidationError:
                    return _problem(
                        request, f"handler returned invalid {header_name} header"
                    )
            content_type = response.headers.get("content-type", "").split(";", 1)[0]
            declared_content = declared.get("content", {})
            if not declared_content:
                return response
            media = declared_content.get(content_type)
            if content_type == "text/markdown":
                return response
            if media is None:
                if not getattr(response, "body", b""):
                    return response
                return _problem(
                    request, "handler returned an undeclared response content type"
                )
            reference = media.get("schema", {}).get("$ref")
            if reference and hasattr(response, "body"):
                try:
                    response_body = response.body
                    if isinstance(response_body, memoryview):
                        response_body = response_body.tobytes()
                    decoded_body = json.loads(response_body)
                    validate_schema(reference.rsplit("/", 1)[-1], decoded_body)
                    if operation.get("operationId") == "completeSetup":
                        expected_etag = f'W/"config:{decoded_body["active_revision"]}"'
                        if response.headers.get("etag") != expected_etag:
                            return _problem(
                                request,
                                "completeSetup ETag does not match persisted body identity",
                            )
                except (
                    json.JSONDecodeError,
                    jsonschema.ValidationError,
                    ValueError,
                ) as error:
                    return _problem(
                        request,
                        f"invalid handler response: {error.message if hasattr(error, 'message') else error}",
                    )
            return response

        return handler
