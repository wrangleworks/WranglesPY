import polars as pl

def file_format(df, name=None, **kwargs):
    pl_df = pl.DataFrame(df)
    format_keys = kwargs.keys()
    if 'conditional_formats' in format_keys:
        formats = kwargs['conditional_formats']
        if not isinstance(formats, dict):
            raise TypeError(f"conditional_formats must be a dictionary, not {type(formats).__name__}")
    else: formats = {}

    if 'header_format' in format_keys:
        headers = kwargs['header_format']
        if not isinstance(headers, dict):
            raise TypeError(f"header_format must be a dictionary, not {type(headers).__name__}")
        headers = kwargs['header_format']
    else: headers = {}

    if name == None:
        name = "output.xlsx"

    if name.split('.')[-1] != 'xlsx':
        raise ValueError(f"name must end with '.xlsx' when formatting: got {name!r}")

    pl_df.write_excel(
            workbook=name,
            worksheet='Not Sheet1',
            table_style='Table Style Medium9',
            header_format=headers,
            # column_widths=col_widths,
            row_heights = 20,
            conditional_formats=formats
        )
