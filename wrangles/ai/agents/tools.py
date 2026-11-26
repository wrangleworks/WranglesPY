"""The four tools exposed to a Copilot session for one selected dataframe."""

import json
import math

import pandas as pd

from ...recipe_wrangles.convert import case as convert_case


TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool}
_CASES = ("lower", "upper", "title", "sentence")


def _check_values(values, kind):
    for value in values:
        if (not isinstance(value, TYPES[kind])
                or (kind in {"integer", "number"} and isinstance(value, bool))
                or (kind == "number" and not math.isfinite(value))):
            raise ValueError("Result value does not match declared output type")


def _read_rows(rows, count, required, allowed):
    """Validate row identity and return only the requested columns in input order."""
    if not isinstance(rows, list) or len(rows) != count:
        raise ValueError("Result must contain every input row exactly once")
    columns = {name: [None] * count for name in required}
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or "row_id" not in row:
            raise ValueError("Each row requires a row_id")
        index = row["row_id"]
        if type(index) is not int or not 0 <= index < count or index in seen:
            raise ValueError("Result row_id is invalid or duplicated")
        seen.add(index)
        names = row.keys() - {"row_id"}
        if not required.keys() <= names <= allowed.keys():
            raise ValueError("Result fields must match declared outputs")
        for name in required:
            columns[name][index] = row[name]
    for name, values in columns.items():
        _check_values(values, required[name]["type"])
    return columns


class DataframeTools:
    def __init__(self, frame, output):
        self.frame = frame.reset_index(drop=True).copy()
        self.output = output
        self.committed = {}
        self.calls = []
        self.result = None

    def _read(self, args):
        records = json.loads(self.frame.to_json(orient="records", date_format="iso", double_precision=15))
        return json.dumps({"rows": [dict(row_id=i, **row) for i, row in enumerate(records)]}, allow_nan=False)

    def _transform(self, args, operation):
        source, destination = args.get("source"), args.get("destination")
        if not isinstance(source, str) or not isinstance(destination, str) or destination not in self.output:
            raise ValueError("Select a source column and a declared destination")
        if destination in self.committed:
            raise ValueError("This column is already committed by a dataframe tool")
        source_rows = args.get("source_rows")
        if source_rows is not None:
            if source in self.frame or source not in self.output or source == destination:
                raise ValueError("source_rows is only for a new model-judged output column")
            # Bind model-chosen group labels to row IDs so their final values and counts agree.
            labels = _read_rows(source_rows, len(self.frame), {"value": self.output[source]}, {"value": {}})["value"]
        elif source not in self.frame:
            raise ValueError("Use an input or previously computed source column")
        if operation == "convert_case":
            if args.get("case") not in _CASES:
                raise ValueError("Use a supported case")
            values = convert_case(self.frame[[source]].copy(), input=source, output=destination,
                                  case=args["case"])[destination].tolist()
        else:
            column = self.frame[source] if source_rows is None else pd.Series(labels, index=self.frame.index)
            try:
                values = column.map(column.value_counts(dropna=False)).tolist()
            except (ValueError, TypeError):
                raise ValueError("count_values requires scalar group values") from None
        _check_values(values, self.output[destination]["type"])
        if source_rows is not None:
            self.frame[source] = labels
            self.committed[source] = labels
        self.frame[destination] = values
        self.committed[destination] = values
        return f"Python wrote {destination} for {len(values)} rows. The column is available to subsequent tools."

    def _submit(self, args):
        pending = {name: spec for name, spec in self.output.items() if name not in self.committed}
        if "rows" in args:
            submitted = _read_rows(args["rows"], len(self.frame), pending, self.output)
        elif pending:
            raise ValueError("submit_results requires rows for the remaining model-judged outputs")
        else:
            submitted = {}
        # Tool-owned columns come directly from Python. Model echoes cannot replace them.
        self.result = {**submitted, **self.committed}
        return "All output columns accepted."

    def definitions(self):
        from copilot.tools import Tool, ToolResult

        def tool(name, description, properties, required, operation, terminal=False):
            async def handle(invocation):
                args = invocation.arguments
                try:
                    if (not isinstance(args, dict) or not set(required) <= args.keys() <= properties.keys()):
                        raise ValueError("Invalid tool arguments")
                    message = operation(args)
                except ValueError as error:
                    return ToolResult(result_type="failure", text_result_for_llm=str(error))
                self.calls.append(name)
                return ToolResult(text_result_for_llm=message)
            return Tool(name=name, description=description, handler=handle, skip_permission=True,
                        is_terminal=terminal, parameters={"type": "object", "properties": properties,
                            "required": required, "additionalProperties": False})

        source = {"type": "string", "description": "Column to operate on"}
        destination = {"type": "string", "enum": list(self.output)}
        pair = {"source": source, "destination": destination}
        row_id = {"type": "integer"}
        rows = {"type": "array", "items": {"type": "object", "additionalProperties": False,
                "properties": {"row_id": row_id, **self.output}, "required": ["row_id"]}}
        groups = {"type": "array", "description": "Only for a new model-judged source. Supply one label for each row.",
                  "items": {"type": "object", "additionalProperties": False, "required": ["row_id", "value"],
                            "properties": {"row_id": row_id, "value": {"type": ["string", "integer", "number", "boolean"]}}}}
        return [
            tool("read_dataframe", "Read selected and computed columns in input row order.", {}, [], self._read),
            tool("convert_case", "Run Wrangles convert.case on every row and commit the destination column.",
                 {**pair, "case": {"type": "string", "enum": list(_CASES)}}, ["source", "destination", "case"],
                 lambda args: self._transform(args, "convert_case")),
            tool("count_values", "Use Python to count occurrences of each source value across the dataframe. "
                 "Reuse a column, or supply source_rows for a new judgment such as a semantic group label.",
                 {**pair, "source_rows": groups}, ["source", "destination"],
                 lambda args: self._transform(args, "count_values")),
            tool("submit_results", "Finish the run. Supply only model-judged fields by row_id. "
                 "When tools wrote all outputs, call with an empty object.", {"rows": rows}, [],
                 self._submit, terminal=True),
        ]
