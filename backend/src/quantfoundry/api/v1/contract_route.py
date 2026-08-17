"""FastAPI route class enforcing canonical request/parameter/response models."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

import jsonschema
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import ValidationError as PydanticValidationError

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


def _resolve_response(response: dict[str, Any]) -> dict[str, Any]:
    if "$ref" not in response:
        return response
    name = response["$ref"].rsplit("/", 1)[-1]
    return canonical_openapi()["components"]["responses"][name]


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
                path_item = canonical_openapi().get("paths", {}).get(path, {})

                def parameter_key(raw_parameter: dict[str, Any]) -> tuple[str, str]:
                    parameter = _resolve_parameter(raw_parameter)
                    return parameter["name"], parameter["in"]

                parameters = {
                    parameter_key(parameter): parameter
                    for parameter in path_item.get("parameters", [])
                }
                parameters.update(
                    {
                        parameter_key(parameter): parameter
                        for parameter in operation.get("parameters", [])
                    }
                )
                for raw_parameter in parameters.values():
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
                            if request.method.upper() in {
                                "GET",
                                "HEAD",
                                "OPTIONS",
                            } and (
                                location == "header" and name.lower() == "x-csrf-token"
                            ):
                                continue
                            if location == "header" and name.lower() in {
                                "idempotency-key",
                                "if-match",
                            }:
                                continue
                            if (
                                location == "header"
                                and name.lower() == "x-csrf-token"
                                and getattr(
                                    request.app.state,
                                    "environment",
                                    os.getenv("QF_ENV", ""),
                                )
                                == "test"
                                and request.headers.get("authorization", "").startswith(
                                    "Bearer "
                                )
                            ):
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
                request_body = operation.get("requestBody")
                if request_body is not None:
                    content = request_body.get("content", {})
                    content_type = (
                        request.headers.get("content-type", "")
                        .split(";", 1)[0]
                        .strip()
                        .lower()
                    )
                    media = content.get(content_type)
                    body = await request.body()
                    if not body:
                        if request_body.get("required", False):
                            raise jsonschema.ValidationError("request body is required")
                    elif media is None:
                        raise jsonschema.ValidationError(
                            "request body content type is not declared"
                        )
                    else:
                        schema = media.get("schema", {})
                        if (
                            content_type.endswith("+json")
                            or content_type == "application/json"
                        ):
                            payload = json.loads(body)
                        else:
                            payload = body.decode("utf-8")
                        reference = schema.get("$ref")
                        if reference:
                            validate_schema(reference.rsplit("/", 1)[-1], payload)
                        else:
                            validate_json_schema(schema, payload)
            except (
                json.JSONDecodeError,
                jsonschema.ValidationError,
                PydanticValidationError,
                UnicodeDecodeError,
                ValueError,
            ) as error:
                from quantfoundry.api.app import invalid_request_response

                return invalid_request_response(request, error)

            response = await original(request)
            raw_declared = operation.get("responses", {}).get(str(response.status_code))
            if raw_declared is None:
                return _problem(
                    request, "handler returned an undocumented response status"
                )
            declared = _resolve_response(raw_declared)
            for header_name, raw_header in declared.get("headers", {}).items():
                if header_name.lower() not in response.headers:
                    if not _resolve_header(raw_header).get("required", False):
                        continue
                    return _problem(
                        request, f"handler omitted required {header_name} header"
                    )
                try:
                    header_schema = _resolve_header(raw_header)["schema"]
                    header_value: Any = response.headers[header_name]
                    if header_schema.get("type") == "integer":
                        header_value = int(header_value)
                    validate_json_schema(header_schema, header_value)
                except jsonschema.ValidationError:
                    return _problem(
                        request, f"handler returned invalid {header_name} header"
                    )
                except (TypeError, ValueError):
                    return _problem(
                        request, f"handler returned invalid {header_name} header"
                    )
            content_type = response.headers.get("content-type", "").split(";", 1)[0]
            declared_content = declared.get("content", {})
            if response.media_type == "text/event-stream":
                if "text/event-stream" not in declared_content:
                    return _problem(
                        request, "handler returned an undeclared SSE content type"
                    )
                return response
            if not declared_content:
                return response
            response_body = getattr(response, "body", b"")
            if isinstance(response_body, memoryview):
                response_body = response_body.tobytes()
            if not response_body:
                return _problem(request, "handler omitted declared response content")
            media = declared_content.get(content_type)
            if media is None:
                return _problem(
                    request, "handler returned an undeclared response content type"
                )
            schema = media.get("schema", {})
            if schema and hasattr(response, "body"):
                try:
                    if (
                        content_type.endswith("+json")
                        or content_type == "application/json"
                    ):
                        decoded_body = json.loads(response_body)
                    else:
                        decoded_body = response_body.decode("utf-8")
                    reference = schema.get("$ref")
                    if reference:
                        validate_schema(reference.rsplit("/", 1)[-1], decoded_body)
                    else:
                        validate_json_schema(schema, decoded_body)
                    if (
                        200 <= response.status_code < 300
                        and operation.get("operationId") == "completeSetup"
                    ):
                        expected_etag = f'W/"config:{decoded_body["active_revision"]}"'
                        if response.headers.get("etag") != expected_etag:
                            return _problem(
                                request,
                                "completeSetup ETag does not match persisted body identity",
                            )
                except (
                    json.JSONDecodeError,
                    jsonschema.ValidationError,
                    PydanticValidationError,
                    UnicodeDecodeError,
                    ValueError,
                ) as error:
                    return _problem(
                        request,
                        f"invalid handler response: {error.message if hasattr(error, 'message') else error}",
                    )
            return response

        return handler
