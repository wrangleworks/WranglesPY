"""
Only for use by the WranglesXL application
"""
import pandas as _pd
from . import memory as _memory

class sheet():
    _schema = {}

    def write(df: _pd.DataFrame, **kwargs):
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
