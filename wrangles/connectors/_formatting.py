import polars as pl

def file_format(
        df,
        workbook: str='output.xlsx',
        worksheet: str='Sheet1',
        **kwargs
        ):
    """
    Apply formatting to an Excel file using Polars and XlsxWriter.
    
    :param df: The pandas DataFrame to be written to Excel.
    :param workbook: The name of the Excel file to create.
    :param worksheet: The name of the worksheet within the Excel file.
    :param kwargs: Additional keyword arguments for formatting options.
    """
    pl_df = pl.DataFrame(df)

    # Set default table style
    if "table_style" not in kwargs:
        kwargs["table_style"] = "Table Style Medium9"

    # Set default header format with valign top
    # Merge so caller-supplied header_format takes precedence
    kwargs["header_format"] = {"valign": "top", **kwargs.get("header_format", {})}

    # Start with any existing column_formats
    col_formats = kwargs.pop("column_formats", {})

    # Inject 'valign': 'top' into every column's format
    # Existing per-column settings take precedence
    for col in pl_df.columns:
        col_formats[col] = {"valign": "top", **col_formats.get(col, {})}

    pl_df.write_excel(
        workbook=workbook,
        worksheet=worksheet,
        column_formats=col_formats,
        **kwargs
    )