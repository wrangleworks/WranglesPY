"""
Only for use by the WranglesXL application
"""
import pandas as _pd
from . import memory as _memory
import logging as _logging
import re as _re


# Names/values follow the syntax already used by the Polars/XlsxWriter
# formatting implementation (see connectors/_formatting.py and the `file`
# connector's `formatting.column_formats`), so recipe authors see one
# consistent formatting syntax across excel.sheet and file, even though
# excel.sheet is rendered by WranglesXL via the Office API rather than
# XlsxWriter.
_FORMATTING_OPTIONS = {"align", "num_format", "bold", "checkbox", "text_wrap"}
_ALIGNMENTS = {"general", "left", "center", "right"}


def _validate_formatting(formatting: dict) -> None:
    """Validate the WranglesXL-specific excel.sheet formatting contract."""
    if not isinstance(formatting, dict):
        raise TypeError("excel.sheet formatting must be a dictionary")

    unknown_groups = set(formatting) - {"columns"}
    if unknown_groups:
        option = sorted(unknown_groups)[0]
        raise ValueError(
            f"excel.sheet formatting option '{option}' is not supported"
        )

    columns = formatting.get("columns")
    if not isinstance(columns, dict) or not columns:
        raise ValueError(
            "excel.sheet formatting columns must be a non-empty dictionary"
        )

    for column, options in columns.items():
        if not isinstance(options, dict) or not options:
            raise ValueError(
                f"excel.sheet formatting for column '{column}' must be a non-empty dictionary"
            )

        unknown_options = set(options) - _FORMATTING_OPTIONS
        if unknown_options:
            option = sorted(unknown_options)[0]
            raise ValueError(
                f"excel.sheet formatting option '{option}' is not supported"
            )

        if "align" in options and options["align"] not in _ALIGNMENTS:
            raise ValueError(
                "excel.sheet align must be general, left, center, or right"
            )
        if (
            "num_format" in options
            and (
                not isinstance(options["num_format"], str)
                or not options["num_format"]
            )
        ):
            raise ValueError(
                "excel.sheet num_format must be a non-empty string"
            )
        for option in ("bold", "checkbox", "text_wrap"):
            if option in options and not isinstance(options[option], bool):
                raise TypeError(f"excel.sheet {option} must be true or false")


def _append_rows_by_column(saved: dict, df: _pd.DataFrame) -> bool:
    """
    Append a dataframe to an orient="split" payload, aligning values by column
    name and adding newly encountered columns in first-seen order.
    """
    new_data = df.to_dict(orient="split")
    saved_columns = saved["columns"]
    new_columns = new_data["columns"]

    # Duplicate labels cannot be aligned by name unambiguously. Preserve the
    # existing behavior for identical layouts, but leave different layouts as
    # separate writes rather than risking a positional shift.
    if (
        saved_columns != new_columns
        and (
            not _pd.Index(saved_columns).is_unique
            or not _pd.Index(new_columns).is_unique
        )
    ):
        return False

    combined_columns = saved_columns + [
        column
        for column in new_columns
        if column not in saved_columns
    ]

    if combined_columns == saved_columns == new_columns:
        saved["data"].extend(new_data["data"])
    else:
        added_columns = len(combined_columns) - len(saved_columns)
        if added_columns:
            saved["data"] = [
                list(row) + [""] * added_columns
                for row in saved["data"]
            ]

        column_positions = {
            column: position
            for position, column in enumerate(combined_columns)
        }
        for row in new_data["data"]:
            aligned_row = [""] * len(combined_columns)
            for column, value in zip(new_columns, row):
                aligned_row[column_positions[column]] = value
            saved["data"].append(aligned_row)

        saved["columns"] = combined_columns

    saved["index"].extend(new_data["index"])
    return True


class sheet():
    _schema = {}

    def write(
        df: _pd.DataFrame,
        variables: dict = None,
        formatting: dict = None,
        **kwargs
    ):
        _logging.info(f": Saving data for Excel Sheet")

        if variables is None:
            variables = {}
        if formatting is not None:
            _validate_formatting(formatting)
            kwargs["formatting"] = formatting

        action = kwargs.get("action", "append")
        try:
            batch_number = int(variables.get("batch_number", 1))
            batch_total = int(variables.get("batch_total", 1))
        except (TypeError, ValueError):
            batch_number = 1
            batch_total = 1

        if action == "overwrite" and batch_total > 1 and batch_number > 1:
            kwargs["action"] = "append"
            action = "append"

        name = kwargs.get("name")
        cell = kwargs.get("cell")

        if action in ("append", "overwrite"):
            for saved in reversed(list(_memory.dataframes.values())):
                if (
                    isinstance(saved, dict)
                    and saved.get("connector") == "excel.sheet.write"
                    and saved.get("name") == name
                    and saved.get("cell") == cell
                    and saved.get("action", "append") in ("append", "overwrite")
                ):
                    # A formatting change starts a new write segment. Do not
                    # merge a later segment back into an older matching one,
                    # which would reorder the emitted rows.
                    if saved.get("formatting") != kwargs.get("formatting"):
                        break
                    if _append_rows_by_column(saved, df):
                        if action == "overwrite":
                            saved["action"] = "overwrite"
                        return

        _memory.write(
            df,
            connector = "excel.sheet.write",
            orient="split",
            **kwargs
        )

    _schema["write"] = """
        type: object
        description: Write to an excel sheet
        additionalProperties: false
        properties:
          name:
            type: string
            description: >-
              Name of the sheet to write to.
              If omitted, will default to the name of the recipe.
          cell:
            type: string
            description: >-
              The top left cell to write the data from.
              Default A1.
          action:
            type: string
            description: |-
              Action to take when writing the data if the sheet already exists. Default append.
              append - add to the existing sheet.
              increment - add a new sheet with an incrementing number.
              overwrite - replace existing sheet.
            enum:
              - overwrite
              - append
              - increment
          freezepanes:
            type: boolean
            description: If true, will freeze the first row. Default false.
          as_table:
            type: boolean
            description: If true, will write the data as an Excel table. Default true.
          formatting:
            type: object
            description: >-
              Formatting to apply to named columns in WranglesXL. Option names
              and values follow the same Polars/XlsxWriter formatting syntax
              used by the `file` connector's `formatting.column_formats`.
            additionalProperties: false
            required:
              - columns
            properties:
              columns:
                type: object
                description: Column headings mapped to their formatting options.
                minProperties: 1
                additionalProperties:
                  type: object
                  additionalProperties: false
                  minProperties: 1
                  properties:
                    align:
                      type: string
                      description: Horizontal alignment for the column values.
                      enum:
                        - general
                        - left
                        - center
                        - right
                    num_format:
                      type: string
                      minLength: 1
                      description: >-
                        Excel number format code for the column values.
                        Matches the `num_format` key used by the Polars/XlsxWriter
                        `column_formats` formatting syntax on the `file` connector.
                    bold:
                      type: boolean
                      description: Whether the column values should be bold.
                    checkbox:
                      type: boolean
                      description: Whether boolean column values should display as checkboxes.
                    text_wrap:
                      type: boolean
                      description: Whether the column values should wrap text within the cell.
        """


class table():
    """Workbook tables, transported by WranglesXL through recipe variables."""
    _schema = {}

    def read(name: str, variables: dict = None):
        _validate_table_name(name)
        snapshots = (variables or {}).get("__excel_tables")
        if not isinstance(snapshots, dict):
            raise RuntimeError("excel.table requires workbook table data supplied by WranglesXL")
        matches = [value for key, value in snapshots.items()
                   if isinstance(key, str) and key.casefold() == name.casefold()]
        if len(matches) != 1:
            raise ValueError(f"Excel table '{name}' was not found or is ambiguous")
        payload = matches[0]
        if not isinstance(payload, dict):
            raise ValueError(f"Excel table '{name}' has an invalid data payload")
        columns, rows = payload.get("columns"), payload.get("data")
        _validate_table_columns(columns)
        if not isinstance(rows, list) or any(
            not isinstance(row, list) or len(row) != len(columns) for row in rows
        ):
            raise ValueError(f"Excel table '{name}' rows must match its headers")
        # The workbook snapshot is input only: never place it in memory outputs.
        return _pd.DataFrame(rows, columns=columns)

    def write(
        df: _pd.DataFrame,
        name: str,
        action: str = "replace",
        variables: dict = None,
        sheet: str = None,
        cell: str = None,
    ):
        _validate_table_name(name)
        _validate_table_columns(df.columns.tolist())
        if action not in ("replace", "append"):
            raise ValueError("excel.table action must be replace or append")
        variables = variables or {}
        if sheet is None:
            recipe_name = variables.get("recipe_name") or "Recipe"
            sheet = _re.sub(r"[\\/*?:\[\]]", "_", f"{recipe_name}-{name}")[:10]
            sheet = sheet.strip("'") or "Recipe"
        if not isinstance(sheet, str) or not sheet or len(sheet) > 31 or (
            _re.search(r"[\\/*?:\[\]]", sheet)
            or sheet.startswith("'") or sheet.endswith("'")
        ):
            raise ValueError("excel.table sheet must be a valid worksheet name (1-31 characters)")
        cell = "A1" if cell is None else cell
        match = _re.fullmatch(r"\$?([A-Za-z]{1,3})\$?([1-9][0-9]*)", cell) if isinstance(cell, str) else None
        if match is None:
            raise ValueError("excel.table cell must be a single A1-style cell address")
        column, row = match.groups()
        column = column.upper()
        column_number = 0
        for letter in column:
            column_number = column_number * 26 + ord(letter) - ord("A") + 1
        if column_number > 16384 or int(row) > 1048576:
            raise ValueError("excel.table cell exceeds Excel worksheet bounds")
        cell = f"{column}{row}"
        batch_number = variables.get("batch_number", 1)
        batch_total = variables.get("batch_total", 1)
        for value in (batch_number, batch_total):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("excel.table batch metadata must be positive integers")
        if batch_number > batch_total:
            raise ValueError("excel.table batch_number exceeds batch_total")
        if action == "replace" and batch_number > 1:
            action = "append"
        # A composed read may introduce NaN/pd.NA/NaT. Emit valid JSON cells
        # without changing the dataframe returned to the recipe caller.
        output = df.astype(object).where(_pd.notna(df), None)
        _memory.write(
            output, connector="excel.table.write", orient="split",
            name=name, action=action, sheet=sheet, cell=cell,
        )

    _schema["read"] = """
        type: object
        description: >-
          Read all body rows and headers from an existing named table in the
          calling Excel workbook. Requires WranglesXL; independent of selection.
          Includes filtered rows and excludes the totals row.
        additionalProperties: false
        required: [name]
        properties:
          name:
            type: string
            minLength: 1
            description: Workbook-wide table name, matched case-insensitively.
        """
    _schema["write"] = """
        type: object
        description: >-
          Write to a named table in the calling Excel workbook, creating it
          on the requested sheet and cell if missing. Headers must
          match the existing column names; column order is aligned by name.
          Calculated/formula columns are not supported in this initial version.
        additionalProperties: false
        required: [name]
        properties:
          name:
            type: string
            minLength: 1
            description: Workbook-wide table name, matched case-insensitively.
          sheet:
            type: string
            minLength: 1
            maxLength: 31
            description: >-
              Worksheet for a new table. Defaults to the first 10 characters
              of recipe_name-table_name (Recipe if recipe_name is unavailable).
              Invalid generated worksheet characters are replaced with underscores.
              Existing tables keep their current worksheet and location.
          cell:
            type: string
            default: A1
            description: >-
              Top-left cell for a new table. Defaults to A1.
              Existing tables keep their current location.
          action:
            type: string
            enum: [replace, append]
            default: replace
            description: >-
              replace clears and replaces body rows, including empty results;
              append adds rows. The table resizes to fit the result.
              Later external batches append after the first replacement.
        """


def _validate_table_name(name):
    if not isinstance(name, str) or not name.strip() or name != name.strip():
        raise ValueError("excel.table name must be a non-empty string without surrounding whitespace")


def _validate_table_columns(columns):
    if not isinstance(columns, list) or not columns or any(
        not isinstance(column, str) or not column.strip() for column in columns
    ):
        raise ValueError("excel.table headers must be non-empty strings")
    if len({column.casefold() for column in columns}) != len(columns):
        raise ValueError("excel.table headers must be unique (case-insensitive)")
