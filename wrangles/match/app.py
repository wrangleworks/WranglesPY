import pandas as pd
from . import exact, rs, patternsAlpha, patterns, predictBrand, merge


# Settings
filename = 'input/data.xlsx'
sheetname = 'Sheet1'
output_name = 'ern-pur'
verbose = False

def run(df_source):
    """
    Main function
    """
    # Load data
    # df_source = pd.read_excel(filename, engine='openpyxl', sheet_name=sheetname)
    df_source = df_source.fillna('')
    
    # Execute matching
    print('Starting Exact')
    # Infer correct brand + part from 'exact' (allowing for variations in special chars) matches
    df_exact = exact.run(df_source, verbose)

    print('Starting RS')
    # Special case to infer correct brand + part from parts that appear to be from RS
    # Due to large volume of RS data available
    df_rs = rs.run(df_source, verbose)

    print('Starting Patterns Alpha')
    # Infer correct brand + part from partcode patterns, preserving letters.
    # e.g. ABCD1234 looks for ABCD####
    df_alpha = patternsAlpha.run(df_source, verbose)

    print('Starting Patterns')
    # Infer correct brand + part from partcode patterns.
    # e.g. ABCD1234 looks for AAAA####
    df_patterns = patterns.run(df_source, verbose)

    print('Starting Predict Brand')
    # Infer correct brand + part from partcode patterns, preserving letters.
    # Does not rely on brands found within the original data, but will suggest when they are absent
    df_predictBrand = predictBrand.run(df_source, verbose)

    # Save results
    df = pd.concat([df_exact, df_rs, df_alpha, df_patterns, df_predictBrand], axis=1)
    # df.to_excel('output/'+ output_name + '-results.xlsx', engine='openpyxl', index=False)

    # Merge together + pick the best result
    print('Merging Potentials')
    df = pd.concat([df_source, df_exact, df_rs, df_alpha, df_patterns, df_predictBrand], axis=1)
    df_results = merge.process(df, output_name)

    return df_results
    print('Finished')