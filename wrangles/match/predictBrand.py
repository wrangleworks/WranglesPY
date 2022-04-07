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


def calculateComplexity(value):
    permutations = 1
    for char in value:
        if char == '#':
            permutations = permutations * 10
        else:
            permutations = permutations * 36

    return permutations


def run(df, verbose=False):
    # Generate a list of all possible brand + part pattern combinations
    part_patterns_all = []
    for idx, row in df.iterrows():
        # Create a list of all parts + convert to patterns
        mpn = [str(row['MPN'])]
        parts_primary = str(row['Parts Primary']).replace(', ', ',').split(',')
        parts_secondary = str(row['Parts Secondary']).replace(', ', ',').split(',')
        parts_all = mpn + parts_primary + parts_secondary
        part_patterns_all = part_patterns_all + [convertPartcodeToPattern(part) for part in parts_all]

    # Compress to unique values
    part_patterns_all = list(set(part_patterns_all))

    # Query server in batches of 1000
    matches = []
    for i in range(0, len(part_patterns_all), 1000):
        placeholders = ', '.join('?' for _ in part_patterns_all[i:i + 1000])
        if len(placeholders):
            sql = 'SELECT Pattern, Brand FROM Partcode_Patterns_Predict_Brand WHERE Pattern IN (%s)' % placeholders
            cursor.execute(sql, part_patterns_all[i:i + 1000])

            for row in cursor.fetchall():
                matches.append([row[0], row[1]])

    # Save to dataframe
    df_matches = pd.DataFrame(matches, columns=['Pattern', 'Brand'])

    # Loop through and find matches
    results = []
    i = 0
    for idx, row in df.iterrows():
        parts_primary = []
        parts_all = []

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

        part_patterns_primary = []
        pattern2part_primary = {}
        # Loop through combinations and add to primary list
        for part in parts_primary:
            if re.search('[a-zA-Z]', str(part)) and calculateComplexity(convertPartcodeToPattern(part)) > 10000000:
                part_patterns_primary.append(convertPartcodeToPattern(part))
                pattern2part_primary[convertPartcodeToPattern(part)] = part

        part_patterns_all = []
        pattern2part_all = {}
        # Loop through combinations and add to all list
        for part in parts_all:
            if re.search('[a-zA-Z]', str(part)) and calculateComplexity(convertPartcodeToPattern(part)) > 10000000:
                part_patterns_all.append(convertPartcodeToPattern(part))
                pattern2part_all[convertPartcodeToPattern(part)] = part

        # Find matches. Primary fields first, then all if that fails
        result = {}
        try:
            match_pattern = df_matches[df_matches['Pattern'].isin(part_patterns_primary)].iloc[0]
            result = {'brand': match_pattern['Brand'], 'part': pattern2part_primary[match_pattern['Pattern']]}
        except:
            try:
                match_pattern = df_matches[df_matches['Pattern'].isin(part_patterns_all)].iloc[0]
                result = {'brand': match_pattern['Brand'], 'part': pattern2part_all[match_pattern['Pattern']]}
            except:
                pass
        
        if result:
            i += 1
            if verbose: print(idx, ' | ', list(parts_all), ' | ', result)

        results.append([row['ID'], result.get('brand',''), result.get('part','')])

    df_results = pd.DataFrame(results, columns=['predict_id', 'predict_brand', 'predict_part'])

    print('Predict Brand: ', i)
    return df_results