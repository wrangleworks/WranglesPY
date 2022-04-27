import re
import pyodbc 
import pandas as pd
from . import config


def cleanPartcode(value):
    value = str(value).upper()
    value = re.sub('[^A-Z0-9]', '', value)
    return value


def run(df, verbose=False):
    cnxn = pyodbc.connect(config.connection_string)
    cursor = cnxn.cursor()

    results = []
    i = 0
    for idx, row in df.iterrows():
        poss_parts = []
        poss_parts_primary = set()
        poss_parts_all = set()

        parts_primary = str(row['Parts Primary']).replace(', ', ',').split(',')
        parts_primary.append(row['MPN'])
        try:
            parts_primary.remove('')
            parts_primary.remove('')
        except:
            pass

        parts_secondary = str(row['Parts Secondary']).replace(', ', ',').split(',')

        parts_all = parts_primary + parts_secondary #+ parts_tertiary
        try:
            parts_all.remove('')
            parts_all.remove('')
        except:
            pass
        
        parts_rs = set()
        for part in parts_all:
            if re.match(r'\d{3}[-.]\d{3,4}$', str(part)):
                parts_rs.add('RS:' + cleanPartcode(part))

        placeholders= ', '.join('?' for _ in parts_rs)
        if len(placeholders):
            query= 'SELECT * FROM ProductsLinks PL INNER JOIN ProductsManu PM ON PL.ProductID = PM.ID WHERE SearchKey IN (%s) ORDER BY MatchScore DESC, PartLength DESC' % placeholders
            cursor.execute(query, list(parts_rs))

        result = {}
        if cursor.rowcount and len(placeholders):
            result_row = cursor.fetchone()
            result['brand'] = result_row[5]
            result['part'] = result_row[7]

        if result:
            i += 1
            if verbose: print(idx, ' | ', list(parts_rs), ' | ', result)
        
        results.append([row['ID'], result.get('brand',''), result.get('part','')])

    df_results = pd.DataFrame(results, columns=['match_rs_id', 'match_rs_brand', 'match_rs_part'])

    print('RS: ', i)
    return df_results