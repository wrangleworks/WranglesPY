import polars as pl

def file_format(
        df,
        workbook: str='output.xlsx',
        worksheet: str='Sheet1',
        **kwargs
        ):
    pl_df = pl.DataFrame(df)

    if workbook.split('.')[-1] != 'xlsx':
        raise ValueError(f"name must end with '.xlsx' when formatting: got {workbook!r}")

    pl_df.write_excel(
        workbook=workbook,
        worksheet=worksheet,
        **kwargs
    )
