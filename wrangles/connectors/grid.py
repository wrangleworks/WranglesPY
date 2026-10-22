"""Data supplied by a grid application to the current recipe invocation."""
import pandas as _pd


class selected_data:
    """Shared selected-data read, independent of the grid application's API."""

    def read(dataframe: _pd.DataFrame = None):
        if dataframe is None or dataframe.empty:
            raise ValueError(
                "Selected data is missing or empty. Select data rows before "
                "running this recipe."
            )
        return dataframe.copy()

    _schema = {"read": """
type: object
description: >-
  Read the selected data supplied to this recipe invocation. Grid applications
  supply the current batch of selected rows. Within a recipe wrangle, this is
  the current parent dataframe, including any preceding transformations.
  Missing or empty selected data raises an error.
additionalProperties: false
properties: {}
"""}
