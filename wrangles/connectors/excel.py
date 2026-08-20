"""
Only for use by the WranglesXL application
"""
import pandas as _pd
from . import memory as _memory
import logging as _logging


# Names/values follow the syntax already used by the Polars/XlsxWriter
# formatting implementation (see connectors/_formatting.py and the `file`
# connector's `formatting.column_formats`), so recipe authors see one
# consistent formatting syntax across excel.sheet and file, even though
# excel.sheet is rendered by WranglesXL via the Office API rather than
# XlsxWriter.
_FORMATTING_OPTIONS = {"align", "num_format", "bold", "checkbox"}
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
        for option in ("bold", "checkbox"):
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
        """
