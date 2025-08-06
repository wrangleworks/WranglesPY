import polars as pl

def file_format(df, name=None, **kwargs):
    pl_df = pl.DataFrame(df)
    format_keys = kwargs.keys()

    if name == None:
        name = "output.xlsx"

    if name.split('.')[-1] != 'xlsx':
        raise ValueError(f"name must end with '.xlsx' when formatting: got {name!r}")
    
    if 'sheet_name' in format_keys:
        sheet_name = kwargs['sheet_name']
        if not isinstance(sheet_name, str):
            raise TypeError(f"sheet_name must be a string, not {type(sheet_name).__name__}")
    else: sheet_name = 'Sheet1'

    ###### To Do: Add column_formats ######

    if 'conditional_formats' in format_keys:
        formats = kwargs['conditional_formats']
        if not isinstance(formats, dict):
            raise TypeError(f"conditional_formats must be a dictionary, not {type(formats).__name__}")
    else: formats = None

    if 'header_format' in format_keys:
        headers = kwargs['header_format']
        if not isinstance(headers, dict):
            raise TypeError(f"header_format must be a dictionary, not {type(headers).__name__}")
        headers = kwargs['header_format']
    else: headers = None

    if 'table_style' in format_keys:
        table_style = kwargs['table_style']
        if not isinstance(table_style, str):
            raise TypeError(f"table_style must be a string, not {type(table_style).__name__}")
    else: table_style = None

    if 'column_widths' in format_keys:
        col_widths = kwargs['column_widths']
        if not isinstance(col_widths, dict):
            raise TypeError(f"column_widths must be a dictionary, not {type(col_widths).__name__}")
        for key, value in col_widths.items():
            if not isinstance(value, (int, float)):
                raise TypeError(f"column width values must be int or float, not {type(value).__name__}")
    else: col_widths = None

    if 'row_heights' in format_keys:
        row_heights = kwargs['row_heights']
        if not isinstance(row_heights, int):
            raise TypeError(f"row_heights must be an integer, not {type(row_heights).__name__}")
    else: row_heights = None

    pl_df.write_excel(
            workbook=name,
            worksheet=sheet_name,
            table_style=table_style,
            header_format=headers,
            column_widths=col_widths,
            row_heights=row_heights,
            conditional_formats=formats
        )
