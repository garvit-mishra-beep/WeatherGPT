"""Validation engine for tool names, JSON arguments, and schema compliance."""

import json
import logging
from typing import Any, Dict, List, Optional

from app.tool_calling.errors import (
    InvalidToolArgumentsError,
    UnknownToolError,
)
from app.tool_calling.models import ToolSchema

logger = logging.getLogger(__name__)


class ToolCallValidator:
    """Validates requested tool calls against declared ToolSchemas."""

    def __init__(self, available_tools: List[ToolSchema]) -> None:
        self.tools_by_name: Dict[str, ToolSchema] = {tool.name: tool for tool in available_tools}

    def validate_tool_name(self, tool_name: str) -> ToolSchema:
        """Ensures tool name is declared and permissible in the current context."""
        if tool_name not in self.tools_by_name:
            logger.warning("Attempted invocation of undeclared tool: '%s'", tool_name)
            raise UnknownToolError(
                tool_name=tool_name,
                available_tools=list(self.tools_by_name.keys()),
            )
        return self.tools_by_name[tool_name]

    def validate_and_parse_arguments(
        self,
        tool_name: str,
        raw_arguments: str,
    ) -> Dict[str, Any]:
        """Parses and validates raw JSON argument string against tool's parameter schema.

        Raises:
            UnknownToolError: If tool_name is not registered.
            InvalidToolArgumentsError: If arguments JSON is malformed or violates schema.
        """
        tool_schema = self.validate_tool_name(tool_name)

        # 1. Parse JSON string
        if not raw_arguments or raw_arguments.strip() == "":
            parsed_args: Dict[str, Any] = {}
        else:
            try:
                parsed_args = json.loads(raw_arguments)
            except json.JSONDecodeError as json_err:
                raise InvalidToolArgumentsError(
                    tool_name=tool_name,
                    reason=f"Arguments must be valid JSON: {str(json_err)}",
                    raw_arguments=raw_arguments,
                ) from json_err

        if not isinstance(parsed_args, dict):
            raise InvalidToolArgumentsError(
                tool_name=tool_name,
                reason=f"Parsed arguments must be a JSON object/dict, got {type(parsed_args).__name__}",
                raw_arguments=raw_arguments,
            )

        # 2. Validate required parameters
        params_spec = tool_schema.parameters
        required_fields = params_spec.get("required", [])
        for req_field in required_fields:
            if req_field not in parsed_args:
                raise InvalidToolArgumentsError(
                    tool_name=tool_name,
                    reason=f"Missing mandatory argument '{req_field}'",
                    raw_arguments=raw_arguments,
                )

        # 3. Validate parameter types if properties are declared
        properties = params_spec.get("properties", {})
        for param_name, param_val in parsed_args.items():
            if param_name in properties:
                prop_spec = properties[param_name]
                expected_type = prop_spec.get("type")
                if not self._check_type(param_val, expected_type):
                    raise InvalidToolArgumentsError(
                        tool_name=tool_name,
                        reason=f"Parameter '{param_name}' expected type '{expected_type}', got '{type(param_val).__name__}'",
                        raw_arguments=raw_arguments,
                    )
            elif params_spec.get("additionalProperties") is False:
                raise InvalidToolArgumentsError(
                    tool_name=tool_name,
                    reason=f"Disallowed additional argument '{param_name}'",
                    raw_arguments=raw_arguments,
                )

        return parsed_args

    def _check_type(self, value: Any, expected_type: Optional[str]) -> bool:
        """Helper validating Python value against JSON Schema primitive types."""
        if expected_type is None or value is None:
            return True
        if expected_type in ("number", "float"):
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected_type in ("integer", "int"):
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type in ("string", "str"):
            return isinstance(value, str)
        if expected_type in ("boolean", "bool"):
            return isinstance(value, bool)
        if expected_type in ("array", "list"):
            return isinstance(value, list)
        if expected_type in ("object", "dict"):
            return isinstance(value, dict)
        return True
