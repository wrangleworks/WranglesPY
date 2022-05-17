import re
import pyodbc
import pandas as pd
from . import config


def cleanPartcode(value):
    value = str(value).upper()
    value = re.sub('[^A-Z0-9]', '', value)
    return value


def calculateComplexity(value):
    permutations = 1
    for char in value:
        if char.isalpha():
            permutations = permutations * 36
        else:
            permutations = permutations * 10

    return permutations


def run(df, verbose=False):
    cnxn = pyodbc.connect(config.connection_string)
    cursor = cnxn.cursor()

    # Generate a list of all possible brand + part pattern combinations
    brand_part_all = []
    for idx, row in df.iterrows():
        # Create a list of all brands
        brands_all = [str(row.get('Manufacturer', ''))] + row.get('Brands Primary', []) + row.get('Brands Secondary', [])

        # Create a list of all parts
        parts_all = [str(row.get('MPN', ''))] + row.get('Parts Primary', []) + row.get('Parts Secondary', [])

        # Remove special chars
        parts_all = [cleanPartcode(part) for part in parts_all]

        brands_all = list(set(brands_all))
        if '' in brands_all: brands_all.remove('')
        
        parts_all = list(set(parts_all))
        if '' in parts_all: parts_all.remove('')

        # Loop through combinations and add with brand
        for brand in brands_all:
            for part in parts_all:
                brand_part_all.append(brand + ':' + part)

        # Loop through combinations and add without brand
        for part in parts_all:
            brand_part_all.append('NULL:' + part)

    # Compress to unique values
    brand_part_all = list(set(brand_part_all))

    # Query server in batches of 1000
    matches = []
    for i in range(0, len(brand_part_all), 1000):
        placeholders = ', '.join('?' for _ in brand_part_all[i:i + 1000])
        if len(placeholders):
            sql = """
                SELECT SearchKey, Brand, ManufacturerID, MatchScore, PartLength
                FROM ProductsLinks PL
                INNER JOIN ProductsManu PM ON PL.ProductID = PM.ID
                WHERE SearchKey IN (%s)
            """ % placeholders
            cursor.execute(sql, brand_part_all[i:i + 1000])

            for row in cursor.fetchall():
                matches.append([row[0], row[1], row[2], row[3], row[4]])

    # Save to dataframe
    df_matches = pd.DataFrame(matches, columns=['ID', 'Brand', 'Part', 'Score', 'Length'])

    # Loop through and find matches
    results = []
    i = 0
    for idx, row in df.iterrows():
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
        
        # Loop through combinations and add to primary list
        brand_part_primary = []
        for brand in brands_primary:
            for part in parts_primary:
                brand_part_primary.append(brand + ':' + cleanPartcode(part))

        # If part is of sufficient complexity, add to list without brands
        null_part_primary = []
        for part in parts_primary:
            if re.search('[a-zA-Z]', str(part)) and calculateComplexity(part) > 10000000:
                null_part_primary.append('NULL:' + cleanPartcode(part))

        # Loop through combinations and add to all list
        brand_part_all = []
        for brand in brands_all:
            for part in parts_all:
                brand_part_all.append(brand + ':' + cleanPartcode(part))

        # If part is of sufficient complexity, add to list without brands
        null_part_all = []
        for part in parts_all:
            if re.search('[a-zA-Z]', str(part)) and calculateComplexity(part) > 10000000:
                null_part_all.append('NULL:' + cleanPartcode(part))

        # Find matches. Primary fields first, then all if that fails
        result = {}
        try:
            # Try primary with brand
            match_pattern = df_matches[df_matches['ID'].isin(brand_part_primary)].sort_values(by=['Score', 'Length'], ascending=(False, False)).iloc[0]
            result = {'brand': match_pattern['Brand'], 'part': match_pattern['Part']}
        except:
            try:
                # Try all with brand
                match_pattern = df_matches[df_matches['ID'].isin(brand_part_all)].sort_values(by=['Score', 'Length'], ascending=(False, False)).iloc[0]
                result = {'brand': match_pattern['Brand'], 'part': match_pattern['Part']}
            except:
                try:
                    # Try primary without brand
                    match_pattern = df_matches[df_matches['ID'].isin(null_part_primary)].sort_values(by=['Score', 'Length'], ascending=(False, False)).iloc[0]
                    result = {'brand': match_pattern['Brand'], 'part': match_pattern['Part']}
                except:
                    try:
                        # Try primary without brand
                        match_pattern = df_matches[df_matches['ID'].isin(null_part_all)].sort_values(by=['Score', 'Length'], ascending=(False, False)).iloc[0]
                        result = {'brand': match_pattern['Brand'], 'part': match_pattern['Part']}
                    except:
                        pass

        if result:
            i += 1
            if verbose: print(idx, ' | ', brand_part_all + null_part_all, ' | ', result)
        
        results.append([row['ID'], result.get('brand',''), result.get('part','')])

    df_results = pd.DataFrame(results, columns=['match_id', 'match_brand', 'match_part'])

    print('Exact: ', i)
    return df_results
