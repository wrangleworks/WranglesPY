"""
Read and write data from a Google Sheets file using Service Account authentication.

The sheet must exist in Google Drive before writing to it.

One-time Google Cloud setup:
    1. Go to console.cloud.google.com and create a project
    2. Enable the Google Sheets API and Google Drive API
    3. Create a Service Account → download the JSON key file
    4. Share the target Google Sheet with the service account email address
       (found in the JSON key as "client_email") — grant it Editor access
"""

import pandas as _pd
import logging as _logging
from typing import Union as _Union


def _get_credentials(credentials_path: _Union[str, dict]):
    """
    Build and return Google Service Account credentials.

    Accepts either a file path (str) or a credentials dict directly - useful
    when credentials are stored in an environment variable and loaded with
    json.loads() rather than written to disk.

    :param credentials_path: File path to the Service Account JSON key, OR a parsed credentials dict
    """
    from google.oauth2 import service_account as _sa

    _SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    if isinstance(credentials_path, dict):
        return _sa.Credentials.from_service_account_info(credentials_path, scopes=_SCOPES)

    return _sa.Credentials.from_service_account_file(credentials_path, scopes=_SCOPES)


def _get_client(credentials_path: _Union[str, dict]):
    """Return an authenticated gspread client."""
    import gspread as _gspread
    creds = _get_credentials(credentials_path)
    return _gspread.authorize(creds)


_schema = {}


def read(
    credentials_path: _Union[str, dict],
    spreadsheet_id: str,
    sheet_name: str = "Sheet1",
    header_row: int = 1,
    evaluate_formulas: bool = False,
) -> _pd.DataFrame:
    """
    Import data from a Google Sheet into a pandas DataFrame.

    >>> from wrangles.connectors import google_sheets
    >>> df = google_sheets.read(
    ...     credentials_path='service_account.json',
    ...     spreadsheet_id='sheet_id_here',
    ...     sheet_name='Sheet1',
    ... )

    :param credentials_path: File path to the Service Account JSON key, OR a credentials dict (e.g. from json.loads())
    :param spreadsheet_id: The spreadsheet ID from the Google Sheets URL
    :param sheet_name: Name of the tab/worksheet to read (default "Sheet1")
    :param header_row: Row number (1-indexed) to use as column headers (default 1)
    :param evaluate_formulas: If True, returns computed cell values instead of raw formulas
    """
    from gspread_dataframe import get_as_dataframe as _get_as_dataframe

    _logging.info(f": Reading data from Google Sheets :: {spreadsheet_id} / {sheet_name}")

    client = _get_client(credentials_path)
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(sheet_name)

    df = _get_as_dataframe(
        worksheet,
        evaluate_formulas=evaluate_formulas,
        header=header_row - 1,
    )

    # Drop empty padding rows/columns that Sheets appends
    df = df.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)

    return df


_schema["read"] = """
type: object
description: Import data from a Google Sheet using Service Account authentication
required:
  - credentials_path
  - spreadsheet_id
properties:
  credentials_path:
    type:
      - string
      - object
    description: File path to the Service Account JSON key, OR a credentials dict (e.g. from json.loads())
  spreadsheet_id:
    type: string
    description: The spreadsheet ID from the Google Sheets URL
  sheet_name:
    type: string
    description: Name of the tab/worksheet to read (default "Sheet1")
  header_row:
    type: integer
    description: Row number (1-indexed) to use as column headers (default 1)
  evaluate_formulas:
    type: boolean
    description: If True, returns computed cell values instead of raw formulas
"""


def write(
    df: _pd.DataFrame,
    credentials_path: _Union[str, dict],
    spreadsheet_id: str,
    sheet_name: str = "Sheet1",
    action: str = "OVERWRITE",
    include_index: bool = False,
    columns: _Union[str, list] = None,
) -> None:
    """
    Write a pandas DataFrame to a Google Sheet.

    The spreadsheet must already exist in Google Drive before writing.
    If the specified sheet_name tab does not exist, it will be created automatically.

    >>> from wrangles.connectors import google_sheets
    >>> google_sheets.write(
    ...     df=df,
    ...     credentials_path='service_account.json',
    ...     spreadsheet_id='sheet_id_here',
    ...     sheet_name='Sheet1',
    ...     action='OVERWRITE',
    ... )

    :param df: DataFrame to write
    :param credentials_path: File path to the Service Account JSON key, OR a credentials dict (e.g. from json.loads())
    :param spreadsheet_id: The spreadsheet ID from the Google Sheets URL. The spreadsheet must exist before writing
    :param sheet_name: Name of the tab/worksheet to write to (created if it doesn't exist)
    :param action: OVERWRITE (default) clears the sheet before writing; APPEND adds rows below existing data
    :param include_index: If True, writes the DataFrame index as the first column
    :param columns: Column name or list of column names to write. Writes all columns if omitted
    """
    import gspread as _gspread
    from gspread_dataframe import set_with_dataframe as _set_with_dataframe

    _logging.info(f": Writing data to Google Sheets :: {spreadsheet_id} / {sheet_name}")

    if columns is not None:
        if isinstance(columns, str):
            columns = [columns]
        df = df[columns]

    client = _get_client(credentials_path)
    spreadsheet = client.open_by_key(spreadsheet_id)

    # Get or create the target tab
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except _gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=sheet_name,
            rows=max(len(df) + 10, 100),
            cols=max(len(df.columns) + 5, 26),
        )

    if action.upper() == "OVERWRITE":
        worksheet.clear()
        _set_with_dataframe(worksheet, df, include_index=include_index, resize=True)

    elif action.upper() == "APPEND":
        rows = df.values.tolist()
        # Coerce non-serialisable types (NaT, Timestamps, etc.) to strings
        safe_rows = [
            [str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for v in row]
            for row in rows
        ]
        worksheet.append_rows(safe_rows, value_input_option="USER_ENTERED")

    else:
        raise ValueError(f"Unsupported action '{action}'. Use 'OVERWRITE' or 'APPEND'.")


_schema["write"] = """
type: object
description: Write data to a Google Sheet using Service Account authentication
required:
  - credentials_path
  - spreadsheet_id
properties:
  credentials_path:
    type:
      - string
      - object
    description: File path to the Service Account JSON key, OR a credentials dict (e.g. from json.loads())
  spreadsheet_id:
    type: string
    description: The spreadsheet ID from the Google Sheets URL. The spreadsheet must exist before writing
  sheet_name:
    type: string
    description: Name of the tab/worksheet to write to (created if it doesn't exist)
  action:
    type: string
    description: OVERWRITE (default) clears the sheet before writing; APPEND adds rows below existing data
  include_index:
    type: boolean
    description: If True, writes the DataFrame index as the first column
  columns:
    type:
      - string
      - array
    description: Column name or list of columns to write. Writes all columns if omitted
"""