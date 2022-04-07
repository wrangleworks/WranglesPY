import re
import pyodbc
import pandas as pd
from . import config


cnxn = pyodbc.connect(config.connection_string)
cursor = cnxn.cursor()


def convertPartcodeToPattern(partcode):
    pattern = str(partcode).upper()
    pattern = re.sub('[^A-Z0-9]', '', pattern)
    pattern = re.sub('[0-9]', '#', pattern)
    return pattern


def run(df, verbose=False):
    # Generate a list of all possible brand + part pattern combinations
    brand_part_all = []
    for idx, row in df.iterrows():
        # Create a list of all brands
        manufacturer = [str(row['Manufacturer'])]
        brands_primary = str(row['Brands Primary']).replace(', ', ',').split(',')
        brands_secondary = str(row['Brands Secondary']).replace(', ', ',').split(',')
        brands_all = manufacturer + brands_primary + brands_secondary

        # Create a list of all parts + convert to patterns
        mpn = [str(row['MPN'])]
        parts_primary = str(row['Parts Primary']).replace(', ', ',').split(',')
        parts_secondary = str(row['Parts Secondary']).replace(', ', ',').split(',')
        parts_all = mpn + parts_primary + parts_secondary
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
            sql = 'SELECT ID, ScoreAdjusted FROM Partcode_Patterns_Alpha WHERE ID IN (%s) ORDER BY ScoreAdjusted DESC' % placeholders
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
        
        # Create a list of all brands
        manufacturer = [str(row['Manufacturer'])]
        brands_primary = list(set(str(row['Brands Primary']).replace(', ', ',').split(',')))
        try:
            brands_primary.remove('')
        except:
            pass
        brands_secondary = str(row['Brands Secondary']).replace(', ', ',').split(',')
        brands_all = manufacturer + brands_primary + brands_secondary
        brands_all = list(set(brands_all))
        try:
            brands_all.remove('')
        except:
            pass

        # Create a list of all parts + convert to patterns
        mpn = [str(row['MPN'])]
        parts_primary = list(set(str(row['Parts Primary']).replace(', ', ',').split(',')))
        try:
            parts_primary.remove('')
        except:
            pass
        parts_secondary = str(row['Parts Secondary']).replace(', ', ',').split(',')
        parts_all = mpn + parts_primary + parts_secondary
        parts_all = list(set(parts_all))
        try:
            parts_all.remove('')
        except:
            pass

        pattern2part_primary = {}
        # Loop through combinations and add to primary list
        for brand in brands_primary:
            for part in parts_primary:
                # Only run if contains a letter. Non-letter codes will be considered in patterns method
                if re.search('[a-zA-Z]', str(part)):
                    brand_part_primary.append(brand + ':' + convertPartcodeToPattern(part))
                    pattern2part_primary[brand + ':' + convertPartcodeToPattern(part)] = {'brand': brand, 'part': part}

        pattern2part_all = {}
        # Loop through combinations and add to all list
        for brand in brands_all:
            for part in parts_all:
                # Only run if contains a letter. Non-letter codes will be considered in patterns method
                if re.search('[a-zA-Z]', str(part)):
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

    df_results = pd.DataFrame(results, columns=['pattern_alpha_id', 'pattern_alpha_brand', 'pattern_alpha_part'])

    print('Patterns Alpha: ', i)
    return df_results