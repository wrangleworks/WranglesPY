import polars as pl
import pandas as pd


DEFAULT_TABLE_STYLE = "Table Style Medium9"


def _unique_table_headers(headers):
    unique_headers = []
    used_headers = set()

    for position, header in enumerate(headers, start=1):
        if header is None or (isinstance(header, str) and header == ""):
            base_header = f"Column{position}"
        else:
            base_header = str(header)
        unique_header = base_header
        suffix = 2
        while unique_header.casefold() in used_headers:
            unique_header = f"{base_header}_{suffix}"
            suffix += 1

        unique_headers.append(unique_header)
        used_headers.add(unique_header.casefold())

    return unique_headers


def default_file_format(
        df,
        workbook: str='output.xlsx',
        worksheet: str='Sheet1',
        **kwargs
        ):
    """
    Apply the default Excel table formatting using Pandas and XlsxWriter.
    """
    excel_kwargs = kwargs.copy()
    excel_kwargs.pop("engine", None)
    writer_kwargs = {}
    for option in ("engine_kwargs", "storage_options"):
        if option in excel_kwargs:
            writer_kwargs[option] = excel_kwargs.pop(option)

    engine_kwargs = writer_kwargs.get("engine_kwargs") or {}
    engine_options = engine_kwargs.get("options") or {}
    if (
        engine_kwargs.get("constant_memory")
        or engine_options.get("constant_memory")
    ):
        raise ValueError(
            "XlsxWriter's constant_memory option is not supported for "
            "formatted Excel tables."
        )

    with pd.ExcelWriter(
        workbook,
        engine="xlsxwriter",
        **writer_kwargs
    ) as writer:
        df.to_excel(
            writer,
            sheet_name=worksheet,
            **excel_kwargs
        )

        worksheet_object = writer.sheets[worksheet]
        workbook_object = writer.book
        startrow = excel_kwargs.get("startrow", 0)
        startcol = excel_kwargs.get("startcol", 0)
        include_header = excel_kwargs.get("header", True) is not False
        include_index = excel_kwargs.get("index", True)
        selected_columns = excel_kwargs.get("columns")
        if selected_columns is None:
            selected_columns = list(df.columns)

        column_count = len(selected_columns)
        if include_index:
            column_count += df.index.nlevels

        top_format = workbook_object.add_format({"valign": "top"})
        if column_count:
            worksheet_object.set_column(
                startcol,
                startcol + column_count - 1,
                None,
                top_format
            )

        if (
            not isinstance(df.columns, pd.MultiIndex)
            and not (include_index and isinstance(df.index, pd.MultiIndex))
            and len(df)
            and column_count
        ):
            lastrow = startrow + len(df)
            if not include_header:
                lastrow -= 1

            table_options = {
                "style": DEFAULT_TABLE_STYLE,
                "header_row": include_header
            }
            if include_header:
                headers = excel_kwargs.get("header", True)
                if headers is True:
                    headers = list(selected_columns)
                else:
                    headers = list(headers)

                if include_index:
                    index_label = excel_kwargs.get("index_label")
                    if index_label is None:
                        index_headers = [
                            name if name is not None else "index"
                            for name in df.index.names
                        ]
                    elif isinstance(index_label, (list, tuple)):
                        index_headers = list(index_label)
                    else:
                        index_headers = [index_label]
                    headers = index_headers + headers

                table_options["columns"] = [
                    {
                        "header": header,
                        "header_format": top_format
                    }
                    for header in _unique_table_headers(headers)
                ]

            worksheet_object.add_table(
                startrow,
                startcol,
                lastrow,
                startcol + column_count - 1,
                table_options
            )

        for cell_format in workbook_object.formats:
            cell_format.set_align("top")

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
        kwargs["table_style"] = DEFAULT_TABLE_STYLE

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