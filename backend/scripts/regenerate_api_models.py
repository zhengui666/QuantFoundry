"""Regenerate committed Pydantic models from the canonical OpenAPI document."""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import yaml

BACKEND_ROOT = Path(__file__).parents[1]
CONTRACT = BACKEND_ROOT.parent / "docs/后端系统技术方案/contracts/openapi-v1.yaml"
OUTPUT = BACKEND_ROOT / "app/generated_api_models.py"


def _literal(values: list[str]) -> str:
    return "Literal[" + ", ".join(repr(value) for value in values) + "]"


def _inject_validator(source: str, class_name: str, body: str) -> str:
    start = source.index(f"class {class_name}(")
    end = source.find("\n\nclass ", start + 1)
    if end < 0:
        end = len(source)
    return source[:end] + "\n\n" + body.rstrip() + source[end:]


def _restore_required_nullable_fields(
    source: str, schemas: dict[str, dict[str, Any]]
) -> str:
    """Correct generator defaults: required+nullable still means required."""

    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    edits: list[tuple[int, int, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name not in schemas:
            continue
        required = set(schemas[node.name].get("required", []))
        for statement in node.body:
            if (
                not isinstance(statement, ast.AnnAssign)
                or not isinstance(statement.target, ast.Name)
                or statement.target.id not in required
                or statement.value is None
            ):
                continue
            value = statement.value
            value_start = offsets[value.lineno - 1] + value.col_offset
            value_end = offsets[cast(int, value.end_lineno) - 1] + cast(
                int, value.end_col_offset
            )
            if isinstance(value, ast.Constant) and value.value is None:
                annotation_end = offsets[
                    cast(int, statement.annotation.end_lineno) - 1
                ] + cast(int, statement.annotation.end_col_offset)
                gap = source[annotation_end:value_end]
                edits.append(
                    (annotation_end, value_end, gap.rsplit("=", 1)[0].rstrip())
                )
            elif isinstance(value, ast.Call):
                value_source = source[value_start:value_end]
                if "default=None" in value_source:
                    edits.append(
                        (
                            value_start,
                            value_end,
                            value_source.replace("default=None", "...", 1),
                        )
                    )
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    return source


def _remove_invalid_root_union_constraints(source: str) -> str:
    """Keep string bounds on leaf roots, not on RootModel wrapper objects."""

    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    edits: list[tuple[int, int, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        root_base = next(
            (
                base
                for base in node.bases
                if isinstance(base, ast.Subscript)
                and isinstance(base.value, ast.Name)
                and base.value.id == "RootModel"
            ),
            None,
        )
        if root_base is None or (
            isinstance(root_base.slice, ast.Name) and root_base.slice.id == "str"
        ):
            continue
        statement = next(
            (
                item
                for item in node.body
                if isinstance(item, ast.AnnAssign)
                and isinstance(item.target, ast.Name)
                and item.target.id == "root"
                and isinstance(item.value, ast.Call)
            ),
            None,
        )
        if statement is None:
            continue
        for keyword in statement.value.keywords:
            if keyword.arg not in {"min_length", "max_length"}:
                continue
            start = offsets[keyword.lineno - 1]
            end = offsets[cast(int, keyword.end_lineno)]
            edits.append((start, end, ""))
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    return source


def _allows_null(schema: dict[str, Any]) -> bool:
    type_value = schema.get("type")
    if type_value == "null" or (isinstance(type_value, list) and "null" in type_value):
        return True
    return any(
        isinstance(branch, dict) and _allows_null(branch)
        for keyword in ("oneOf", "anyOf")
        for branch in schema.get(keyword, [])
    )


def _without_none(annotation: ast.expr) -> ast.expr:
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        if (
            isinstance(annotation.right, ast.Constant)
            and annotation.right.value is None
        ):
            return annotation.left
        if isinstance(annotation.left, ast.Constant) and annotation.left.value is None:
            return annotation.right
        annotation.left = _without_none(annotation.left)
        annotation.right = _without_none(annotation.right)
    return annotation


def _reject_explicit_null_for_optional_fields(
    source: str, schemas: dict[str, dict[str, Any]]
) -> str:
    """Optional JSON properties may be absent but cannot silently accept null."""

    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    edits: list[tuple[int, int, str]] = []
    for node in tree.body:
        schema = schemas.get(node.name) if isinstance(node, ast.ClassDef) else None
        if not isinstance(node, ast.ClassDef) or not isinstance(schema, dict):
            continue
        required = set(schema.get("required", []))
        properties = schema.get("properties", {})
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign) or not isinstance(
                statement.target, ast.Name
            ):
                continue
            name = statement.target.id
            property_schema = properties.get(name)
            if (
                name in required
                or not isinstance(property_schema, dict)
                or _allows_null(property_schema)
                or "None" not in ast.unparse(statement.annotation)
            ):
                continue
            annotation_start = (
                offsets[statement.annotation.lineno - 1]
                + statement.annotation.col_offset
            )
            annotation_end = offsets[
                cast(int, statement.annotation.end_lineno) - 1
            ] + cast(int, statement.annotation.end_col_offset)
            annotation_source = ast.unparse(_without_none(statement.annotation))
            edits.append(
                (
                    annotation_start,
                    annotation_end,
                    annotation_source,
                )
            )
            if (
                isinstance(statement.value, ast.Constant)
                and statement.value.value is None
            ):
                value_start = (
                    offsets[statement.value.lineno - 1] + statement.value.col_offset
                )
                value_end = offsets[cast(int, statement.value.end_lineno) - 1] + cast(
                    int, statement.value.end_col_offset
                )
                edits.append(
                    (value_start, value_end, f"cast({annotation_source}, None)")
                )
            elif isinstance(statement.value, ast.Call):
                value_start = (
                    offsets[statement.value.lineno - 1] + statement.value.col_offset
                )
                value_end = offsets[cast(int, statement.value.end_lineno) - 1] + cast(
                    int, statement.value.end_col_offset
                )
                value_source = source[value_start:value_end]
                if "default=None" in value_source:
                    edits.append(
                        (
                            value_start,
                            value_end,
                            value_source.replace(
                                "default=None",
                                f"default=cast({annotation_source}, None)",
                                1,
                            ),
                        )
                    )
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    return source


def _restore_nullable_annotations(
    source: str, schemas: dict[str, dict[str, Any]]
) -> str:
    """Preserve nullable enums that the upstream generator narrows incorrectly."""

    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    edits: list[tuple[int, int, str]] = []
    for node in tree.body:
        schema = schemas.get(node.name) if isinstance(node, ast.ClassDef) else None
        if not isinstance(node, ast.ClassDef) or not isinstance(schema, dict):
            continue
        properties = schema.get("properties", {})
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign) or not isinstance(
                statement.target, ast.Name
            ):
                continue
            property_schema = properties.get(statement.target.id)
            annotation_source = ast.unparse(statement.annotation)
            if (
                not isinstance(property_schema, dict)
                or not _allows_null(property_schema)
                or "None" in annotation_source
            ):
                continue
            start = (
                offsets[statement.annotation.lineno - 1]
                + statement.annotation.col_offset
            )
            end = offsets[cast(int, statement.annotation.end_lineno) - 1] + cast(
                int, statement.annotation.end_col_offset
            )
            edits.append((start, end, f"{annotation_source} | None"))
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    return source


def _advertise_write_only_credential(source: str) -> str:
    tree = ast.parse(source)
    target_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "SetupProviderConnectionValidationRequest"
    )
    statement = next(
        node
        for node in target_class.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "credential"
    )
    assert isinstance(statement.value, ast.Call)
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    end = offsets[cast(int, statement.value.end_lineno) - 1] + cast(
        int, statement.value.end_col_offset
    )
    return source[: end - 1] + ", json_schema_extra={'writeOnly': True})" + source[end:]


def _advertise_min_properties(source: str, class_name: str) -> str:
    start = source.index(f"class {class_name}(")
    config_start = source.index("model_config = ConfigDict(", start)
    config_end = source.index("    )", config_start)
    config = source[config_start:config_end]
    config += "        json_schema_extra={'minProperties': 1},\n"
    return source[:config_start] + config + source[config_end:]


def _advertise_validation_schema(
    source: str, class_name: str, validation_schema: dict[str, Any]
) -> str:
    tree = ast.parse(source)
    target = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    start = offsets[target.lineno - 1]
    end = offsets[cast(int, target.end_lineno) - 1] + cast(int, target.end_col_offset)
    class_source = source[start:end]
    config_marker = "    model_config = ConfigDict("
    config_start = class_source.find(config_marker)
    if config_start < 0:
        insert_at = source.find("\n", start) + 1
        config = f"    model_config = ConfigDict(\n        json_schema_extra={validation_schema!r},\n    )\n"
        return source[:insert_at] + config + source[insert_at:]
    config_end = class_source.find("    )", config_start)
    if config_end < 0:
        raise ValueError(f"{class_name} has an unterminated model_config")
    absolute_end = start + config_end
    config = class_source[config_start:config_end]
    config += f"        json_schema_extra={validation_schema!r},\n"
    return source[: start + config_start] + config + source[absolute_end:]


def _inline_validation_refs(
    value: Any, schemas: dict[str, dict[str, Any]], stack: frozenset[str] = frozenset()
) -> Any:
    if isinstance(value, list):
        return [_inline_validation_refs(item, schemas, stack) for item in value]
    if not isinstance(value, dict):
        return value
    reference = value.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/components/schemas/"):
        name = reference.rsplit("/", 1)[-1]
        if name in schemas and name not in stack:
            return _inline_validation_refs(
                deepcopy(schemas[name]), schemas, stack | {name}
            )
    return {
        key: _inline_validation_refs(item, schemas, stack)
        for key, item in value.items()
    }


def _restore_singleton_const_object_ids(
    source: str, schemas: dict[str, dict[str, Any]]
) -> str:
    """Keep singleton locator IDs as Literal rather than unconstrained strings."""

    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    edits: list[tuple[int, int, str]] = []

    def const_strings(value: Any) -> list[str]:
        if isinstance(value, list):
            return [item for child in value for item in const_strings(child)]
        if not isinstance(value, dict):
            return []
        values = [value["const"]] if isinstance(value.get("const"), str) else []
        return values + [
            item for child in value.values() for item in const_strings(child)
        ]

    for node in tree.body:
        schema = schemas.get(node.name) if isinstance(node, ast.ClassDef) else None
        if not isinstance(node, ast.ClassDef) or not isinstance(schema, dict):
            continue
        object_id_schema = schema.get("properties", {}).get("object_id", {})
        const_values = list(dict.fromkeys(const_strings(object_id_schema)))
        if not const_values:
            continue
        statement = next(
            (
                item
                for item in node.body
                if isinstance(item, ast.AnnAssign)
                and isinstance(item.target, ast.Name)
                and item.target.id == "object_id"
            ),
            None,
        )
        if statement is None:
            continue
        annotation_source = ast.unparse(statement.annotation)
        if "str" not in annotation_source:
            continue
        replacement = annotation_source.replace("str", _literal(const_values), 1)
        start = (
            offsets[statement.annotation.lineno - 1] + statement.annotation.col_offset
        )
        end = offsets[cast(int, statement.annotation.end_lineno) - 1] + cast(
            int, statement.annotation.end_col_offset
        )
        edits.append((start, end, replacement))
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    return source


def _merge_structural_all_of(value: Any, schemas: dict[str, dict[str, Any]]) -> Any:
    """Flatten structural inheritance for codegen; retain conditional allOf."""

    if isinstance(value, list):
        return [_merge_structural_all_of(item, schemas) for item in value]
    if not isinstance(value, dict):
        return value
    current = deepcopy(value)
    branches = current.get("allOf")
    if (
        isinstance(branches, list)
        and len(branches) == 1
        and isinstance(branches[0], dict)
        and not any(key in branches[0] for key in ("if", "then", "else"))
    ):
        branch = deepcopy(branches[0])
        if set(branch) == {"$ref"}:
            branch = deepcopy(schemas[branch["$ref"].rsplit("/", 1)[-1]])
        current.pop("allOf")
        for key, branch_value in branch.items():
            if key == "properties" and isinstance(branch_value, dict):
                current[key] = {
                    **cast(dict[str, Any], current.get(key, {})),
                    **branch_value,
                }
            elif key == "required" and isinstance(branch_value, list):
                current[key] = list(
                    dict.fromkeys(
                        [*cast(list[Any], current.get(key, [])), *branch_value]
                    )
                )
            elif key not in current:
                current[key] = branch_value
    elif isinstance(branches, list) and all(
        isinstance(branch, dict)
        and not any(key in branch for key in ("if", "then", "else", "oneOf", "anyOf"))
        for branch in branches
    ):
        resolved: list[dict[str, Any]] = []
        for branch in branches:
            if set(branch) == {"$ref"}:
                name = branch["$ref"].rsplit("/", 1)[-1]
                resolved.append(deepcopy(schemas[name]))
            else:
                resolved.append(deepcopy(branch))
        if all(
            not any(key in branch for key in ("if", "then", "else", "oneOf", "anyOf"))
            for branch in resolved
        ):
            current.pop("allOf")
            properties = dict(current.pop("properties", {}))
            required = list(current.pop("required", []))
            for branch in resolved:
                properties.update(branch.pop("properties", {}))
                required.extend(branch.pop("required", []))
                current.update(branch)
            if properties:
                current["properties"] = properties
            if required:
                current["required"] = list(dict.fromkeys(required))
    return {
        key: _merge_structural_all_of(item, schemas) for key, item in current.items()
    }


def generate(output: Path = OUTPUT) -> str:
    specification: dict[str, Any] = yaml.safe_load(CONTRACT.read_text())
    schemas = specification["components"]["schemas"]
    generation_specification = _merge_structural_all_of(specification, schemas)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="qf-generated-api-", suffix=".py"
    )
    os.close(descriptor)
    work_output = Path(temporary_name)
    with tempfile.TemporaryDirectory() as input_directory:
        generation_input = Path(input_directory) / CONTRACT.name
        generation_input.write_text(
            yaml.safe_dump(generation_specification, sort_keys=False)
        )
        command = [
            sys.executable,
            "-m",
            "datamodel_code_generator",
            "--input",
            str(generation_input),
            "--input-file-type",
            "openapi",
            "--output",
            str(work_output),
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            "3.13",
            "--use-standard-collections",
            "--use-union-operator",
            "--field-constraints",
            "--strict-nullable",
            "--enum-field-as-literal",
            "all",
            "--use-default-kwarg",
            "--collapse-root-models",
            "--use-schema-description",
            "--use-field-description",
            "--disable-timestamp",
        ]
        subprocess.run(command, check=True)
        source = work_output.read_text()
    source = source.replace(
        "from datetime import date\n",
        "from datetime import date\nfrom decimal import Decimal, InvalidOperation\n",
    )
    source = re.sub(
        r"from typing import [^\n]+",
        "from typing import Any, Annotated, Literal, cast",
        source,
        count=1,
    ).replace(
        "from pydantic import AnyUrl, AwareDatetime, BaseModel, ConfigDict, Field, RootModel",
        "from jsonschema import Draft202012Validator\n\n"
        "from pydantic import (\n"
        "    AnyUrl,\n"
        "    AwareDatetime,\n"
        "    BaseModel,\n"
        "    ConfigDict,\n"
        "    Field,\n"
        "    RootModel,\n"
        "    model_validator,\n"
        ")",
    )
    source = re.sub(
        r"\n\nclass ForwardReturnHorizon\(RootModel\[int\]\):\n"
        r"    root: int = Field\(\.\.\., ge=1\)\n",
        "",
        source,
    ).replace(
        "list[ForwardReturnHorizon]",
        "list[Annotated[int, Field(ge=1)]]",
    )
    source = _remove_invalid_root_union_constraints(source)
    source = _restore_nullable_annotations(source, schemas)
    source = _reject_explicit_null_for_optional_fields(source, schemas)
    source = _restore_required_nullable_fields(source, schemas)
    source = _restore_singleton_const_object_ids(source, schemas)
    source = source.replace(
        "values: list[str] = Field(..., min_length=1)",
        "values: list[str] = Field(..., min_length=1, json_schema_extra={'uniqueItems': True})",
        1,
    )
    source = source.replace(
        "search_space: list[ExperimentSearchSetDimension | ExperimentSearchRangeDimension]",
        "search_space: list[Annotated[ExperimentSearchSetDimension | ExperimentSearchRangeDimension, Field(discriminator='kind')]]",
        1,
    )
    source = _advertise_write_only_credential(source)
    for name, schema in schemas.items():
        all_of = schema.get("allOf")
        if isinstance(all_of, list):
            validation_schema = {
                keyword: schema[keyword]
                for keyword in ("allOf", "dependentRequired")
                if keyword in schema
            }
            validation_schema = _inline_validation_refs(validation_schema, schemas)
            source = _advertise_validation_schema(source, name, validation_schema)
            source = _inject_validator(
                source,
                name,
                "    @model_validator(mode='after')\n"
                "    def validate_conditional_constraints(self):\n"
                f"        validator = Draft202012Validator({validation_schema!r})\n"
                "        errors = sorted(\n"
                "            validator.iter_errors(self.model_dump(mode='json', by_alias=True, exclude_unset=True)),\n"
                "            key=lambda error: list(error.absolute_path),\n"
                "        )\n"
                "        if errors:\n"
                "            raise ValueError(errors[0].message)\n"
                "        return self\n",
            )
    source = _advertise_min_properties(source, "ExperimentReproduceExecutionOverrides")
    source = _advertise_min_properties(source, "AgentConfigUpdate")
    source = _inject_validator(
        source,
        "ExperimentReproduceExecutionOverrides",
        "    @model_validator(mode='after')\n"
        "    def require_at_least_one_override(self):\n"
        "        if not self.model_fields_set:\n"
        "            raise ValueError('at least one execution override is required')\n"
        "        return self\n",
    )
    source = _inject_validator(
        source,
        "AgentConfigUpdate",
        "    @model_validator(mode='after')\n"
        "    def require_at_least_one_update(self):\n"
        "        if not self.model_fields_set:\n"
        "            raise ValueError('at least one config update is required')\n"
        "        return self\n",
    )
    source = _inject_validator(
        source,
        "ExperimentSearchSetDimension",
        "    @model_validator(mode='after')\n"
        "    def validate_typed_values(self):\n"
        "        if len(set(self.values)) != len(self.values):\n"
        "            raise ValueError('SET values must be unique')\n"
        "        if self.value_type == 'INTEGER':\n"
        "            try:\n"
        "                values = [Decimal(value) for value in self.values]\n"
        "            except InvalidOperation as error:\n"
        "                raise ValueError('INTEGER set values must be numeric integers') from error\n"
        "            if any(not value.is_finite() for value in values):\n"
        "                raise ValueError('INTEGER set values must be finite')\n"
        "            if any(value != value.to_integral_value() for value in values):\n"
        "                raise ValueError('INTEGER set values must be integral')\n"
        "        return self\n",
    )
    source = _inject_validator(
        source,
        "ExperimentSearchRangeDimension",
        "    @model_validator(mode='after')\n"
        "    def validate_ordered_range(self):\n"
        "        try:\n"
        "            minimum = Decimal(self.minimum)\n"
        "            maximum = Decimal(self.maximum)\n"
        "            step = Decimal(self.step)\n"
        "        except InvalidOperation as error:\n"
        "            raise ValueError('range bounds must be finite decimals') from error\n"
        "        if minimum >= maximum:\n"
        "            raise ValueError('minimum must be less than maximum')\n"
        "        if step <= 0:\n"
        "            raise ValueError('step must be positive')\n"
        "        if self.value_type == 'INTEGER' and any(\n"
        "            value != value.to_integral_value() for value in (minimum, maximum, step)\n"
        "        ):\n"
        "            raise ValueError('INTEGER ranges require integral bounds and step')\n"
        "        return self\n",
    )
    missing_root_models = []
    for name in (
        "CanonicalErrorCode",
        "SetupProviderKind",
        "ResearchStatus",
        "AgentRoleKey",
        "ExperimentStatus",
        "ExperimentValidityState",
        "EventType",
    ):
        missing_root_models.append(
            f"\n\nclass {name}(RootModel[{_literal(schemas[name]['enum'])}]):\n"
            f"    root: {_literal(schemas[name]['enum'])}\n"
        )
    missing_root_models.extend(
        [
            "\n\nclass ConfigurationValueWrite(\n"
            "    RootModel[ConfigurationValueWrite1 | ConfigurationValueWrite2]\n"
            "):\n"
            "    root: ConfigurationValueWrite1 | ConfigurationValueWrite2\n",
            "\n\nclass ConfigurationValueView(BaseModel):\n"
            "    model_config = ConfigDict(\n"
            "        extra='forbid',\n"
            "        json_schema_extra={\n"
            "            'oneOf': [\n"
            "                {'properties': {'sensitivity': {'enum': ['PUBLIC', 'MASKED']}}, 'required': ['sensitivity', 'value']},\n"
            "                {'properties': {'sensitivity': {'const': 'SECRET'}, 'value': {'type': 'null'}, 'masked_hint': {'type': 'string', 'minLength': 1, 'maxLength': 80}}, 'required': ['sensitivity', 'value', 'masked_hint']},\n"
            "            ]\n"
            "        },\n"
            "    )\n"
            "    key: str = Field(..., pattern=r'^[a-z][a-z0-9]*(\\.[a-z0-9_-]+)+$')\n"
            "    sensitivity: Literal['PUBLIC', 'MASKED', 'SECRET']\n"
            "    configured: bool\n"
            "    value: str | float | bool | dict[str, Any] | list | None\n"
            "    masked_hint: str | None = Field(..., max_length=80)\n"
            "\n"
            "    @model_validator(mode='after')\n"
            "    def validate_secret_view(self):\n"
            "        if self.sensitivity == 'SECRET' and (self.value is not None or not self.masked_hint):\n"
            "            raise ValueError('secret configuration values must be masked')\n"
            "        return self\n",
            "\n\nclass ExperimentSearchDimension(\n"
            "    RootModel[Annotated[ExperimentSearchSetDimension | ExperimentSearchRangeDimension, Field(discriminator='kind')]]\n"
            "):\n"
            "    root: Annotated[ExperimentSearchSetDimension | ExperimentSearchRangeDimension, Field(discriminator='kind')]\n",
            "\n\nclass ExperimentSearchResult(\n"
            "    RootModel[Annotated[ExperimentSearchResultNotApplicable | ExperimentSearchResultPending | ExperimentSearchResultRunning | ExperimentSearchResultCompleted | ExperimentSearchResultFailed, Field(discriminator='state')]]\n"
            "):\n"
            "    root: Annotated[ExperimentSearchResultNotApplicable | ExperimentSearchResultPending | ExperimentSearchResultRunning | ExperimentSearchResultCompleted | ExperimentSearchResultFailed, Field(discriminator='state')]\n",
            "\n\nclass StrategyLatestBacktest(\n"
            "    RootModel[StrategyLatestBacktestAvailable | StrategyLatestBacktestUnavailable]\n"
            "):\n"
            "    root: StrategyLatestBacktestAvailable | StrategyLatestBacktestUnavailable\n",
        ]
    )
    schema_names = ",\n    ".join(repr(name) for name in schemas)
    source += "".join(missing_root_models)
    source += f"\n\nSCHEMA_NAMES = (\n    {schema_names},\n)\n"
    source += "\n__all__ = [*SCHEMA_NAMES, 'SCHEMA_NAMES']\n"
    work_output.write_text(source)
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", str(work_output)], check=True
    )
    subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--fix", str(work_output)], check=True
    )
    source = work_output.read_text()
    output.write_text(source)
    work_output.unlink(missing_ok=True)
    return source


if __name__ == "__main__":
    if "--check" in sys.argv:
        committed = OUTPUT.read_text()
        with tempfile.TemporaryDirectory() as directory:
            candidate = generate(Path(directory) / OUTPUT.name)
        if candidate != committed:
            raise SystemExit("generated_api_models.py is stale; regenerate it")
    else:
        generate()
