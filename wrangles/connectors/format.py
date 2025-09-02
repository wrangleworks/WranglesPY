import polars as pl

def file_format(
        df,
        workbook: str='output.xlsx',
        worksheet: str='Sheet1',
        **kwargs
        ):
    pl_df = pl.DataFrame(df)

    # Set default table style
    if "table_style" not in kwargs:
        kwargs["table_style"] = "Table Style Medium9"

    pl_df.write_excel(
        workbook=workbook,
        worksheet=worksheet,
        **kwargs
    )