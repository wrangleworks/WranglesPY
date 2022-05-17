import re
import pyodbc
import pandas as pd
from . import config


def convertPartcodeToPattern(partcode):
    pattern = str(partcode).upper()
    pattern = re.sub('[^A-Z0-9]', '', pattern)
    pattern = re.sub('[A-Z]', 'A', pattern)
    pattern = re.sub('[0-9]', '#', pattern)
    return pattern


def run(df, verbose=False):
    cnxn = pyodbc.connect(config.connection_string)
    cursor = cnxn.cursor()

    # Generate a list of all possible brand + part pattern combinations
    brand_part_all = []
    for idx, row in df.iterrows():
        # Create a list of all brands
        brands_all = [str(row.get('Manufacturer', ''))] + row.get('Brands Primary', []) + row.get('Brands Secondary', [])

        # Create a list of all parts + convert to patterns
        parts_all = [str(row.get('MPN', ''))] + row.get('Parts Primary', []) + row.get('Parts Secondary', [])
        part_patterns_all = [convertPartcodeToPattern(part) for part in parts_all]

        # Loop through combinations and add to main list
        for brand in brands_all:
            for part in part_patterns_all:
                brand_part_all.append(brand + ':' + part)

    # Compress to unique values
    brand_part_all = list(set(brand_part_all))

    # Query server in batches of 1000
    matches = []
    for i in range(0, len(brand_part_all), 1000):
        placeholders = ', '.join('?' for _ in brand_part_all[i:i + 1000])
        if len(placeholders):
            sql = """
                SELECT ID, ScoreAdjusted
                FROM Partcode_Patterns
                WHERE ID IN (%s)
                ORDER BY ScoreAdjusted DESC
            """ % placeholders
            cursor.execute(sql, brand_part_all[i:i + 1000])

            for row in cursor.fetchall():
                matches.append([row[0], row[1]])

    # Save to dataframe
    df_matches = pd.DataFrame(matches, columns=['ID', 'Score'])

    # Loop through and find matches
    results = []
    i = 0
    for idx, row in df.iterrows():
        brand_part_primary = []
        brand_part_all = []
        
        # Create a list of primary and all brands
        manufacturer = [str(row.get('Manufacturer', ''))]
        brands_primary = list(set(row.get('Brands Primary',[])))
        if '' in brands_primary: brands_primary.remove('')

        brands_secondary = list(set(row.get('Brands Secondary',[])))
        brands_all = manufacturer + brands_primary + brands_secondary
        brands_all = list(set(brands_all))
        if '' in brands_all: brands_all.remove('')

        # Create a list of primary and all parts
        mpn = [str(row.get('MPN', ''))]
        parts_primary = list(set(row.get('Parts Primary',[])))
        if '' in parts_primary: parts_primary.remove('')

        parts_secondary = list(set(row.get('Parts Secondary',[])))
        parts_all = mpn + parts_primary + parts_secondary
        parts_all = list(set(parts_all))
        if '' in parts_all: parts_all.remove('')

        pattern2part_primary = {}
        # Loop through combinations and add to primary list
        for brand in brands_primary:
            for part in parts_primary:
                brand_part_primary.append(brand + ':' + convertPartcodeToPattern(part))
                pattern2part_primary[brand + ':' + convertPartcodeToPattern(part)] = {'brand': brand, 'part': part}

        pattern2part_all = {}
        # Loop through combinations and add to all list
        for brand in brands_all:
            for part in parts_all:
                brand_part_all.append(brand + ':' + convertPartcodeToPattern(part))
                pattern2part_all[brand + ':' + convertPartcodeToPattern(part)] = {'brand': brand, 'part': part}

        # Find matches. Primary fields first, then all if that fails
        result = {}
        try:
            match_pattern = df_matches[df_matches['ID'].isin(brand_part_primary)].sort_values(by=['Score'], ascending=False).iloc[0]['ID']
            result = pattern2part_primary[match_pattern]
        except:
            try:
                match_pattern = df_matches[df_matches['ID'].isin(brand_part_all)].sort_values(by=['Score'], ascending=False).iloc[0]['ID']
                result = pattern2part_all[match_pattern]
            except:
                pass
        
        if result:
            i += 1
            if verbose: print(idx, ' | ', list(brand_part_all), ' | ', result)

        results.append([row['ID'], result.get('brand',''), result.get('part','')])

    df_results = pd.DataFrame(results, columns=['patterns_id', 'patterns_brand', 'patterns_part'])

    print('Patterns: ', i)
    return df_results