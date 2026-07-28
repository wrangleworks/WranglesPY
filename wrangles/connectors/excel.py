"""
Only for use by the WranglesXL application
"""
import pandas as _pd
from . import memory as _memory
import logging as _logging

class sheet():
    _schema = {}

    def write(df: _pd.DataFrame, variables: dict = None, **kwargs):
        _logging.info(f": Saving data for Excel Sheet")

        if variables is None:
            variables = {}

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
                    and saved.get("columns") == df.columns.tolist()
                ):
                    new_data = df.to_dict(orient="split")
                    saved["data"].extend(new_data["data"])
                    saved["index"].extend(new_data["index"])
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
        """
