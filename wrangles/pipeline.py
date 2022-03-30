"""
Create and execute Wrangling pipelines
"""
import yaml
import pandas
import logging
from . import select as _select
from . import format as _format
from . import classify as _classify
from . import extract as _extract
from . import ww_pd

logging.getLogger().setLevel(logging.INFO)


def _load_config_file(config_file, params):
    """
    Load yaml config file + replace any placeholder variables
    """
    config = None
    with open(config_file, "r") as f:
        conf_file = f.read()
        for key, val in params.items():
            conf_file = conf_file.replace(r"{{" + key + r"}}", val)
        config = yaml.safe_load(conf_file)
    return config


def _import_file(file_name, sheet_name):
    """
    Import data
    """
    df = None

    if file_name.split('.')[-1] in ['xlsx', 'xlsm', 'xls']:
        df = pandas.read_excel(file_name, dtype='object', sheet_name=sheet_name)
        df = df.fillna('')
    elif file_name.split('.')[-1] in ['csv', 'txt']:
        df = pandas.read_csv(file_name)
        df = df.fillna('')

    return df


def _export_file(conf_export, df):
    """
    Export file
    """
    output_df = pandas.DataFrame(dtype='object')
    for field in conf_export['fields']:
        output_df[field] = df[field]

    if conf_export['name'].split('.')[-1] in ['xlsx', 'xlsm', 'xls']:
        output_df.to_excel(conf_export['name'], index=False)
    elif conf_export['name'].split('.')[-1] in ['csv', 'txt']:
        output_df.to_csv(conf_export['name'], index=False)

    return output_df


def _execute_wrangles(wrangles_config, df):
    for step in wrangles_config:
        for wrangle, params in step.items():
            logging.info(f": Wrangling :: {wrangle} :: {params['input']} >> {params['output']}")

            match wrangle:
                case 'rename':
                    # Rename a column
                    df[params['output']] = df[params['input']].tolist()

                case 'join':
                    # Join a list to a string e.g. ['ele1', 'ele2', 'ele3'] -> 'ele1,ele2,ele3'
                    df[params['output']] = _format.join_list(df[params['input']].tolist(), params['parameters']['char'])

                case 'concatenate':
                    # Concatenate multiple inputs into one
                    df[params['output']] = _format.concatenate(df[params['input']].astype(str).values.tolist(), params['parameters']['char'])

                case 'split':
                    df[params['output']] = _format.split(df[params['input']].astype(str).tolist(), params['parameters']['char'])

                case 'convert.data_type':
                    if params['parameters']['dataType'] == 'float':
                        df[params['output']] = df[params['input']].astype(float).tolist()
                    else:
                        df[params['output']] = df[params['input']].tolist()
                
                case 'convert.case':
                    if params['parameters']['case'].lower() == 'lower':
                        df[params['output']] = df[params['input']].str.lower()
                    elif params['parameters']['case'].lower() == 'upper':
                        df[params['output']] = df[params['input']].str.lower()
                    elif params['parameters']['case'].lower() == 'title':
                        df[params['output']] = df[params['input']].str.title()
                    elif params['parameters']['case'].lower() == 'sentence':
                        df[params['output']] = df[params['input']].str.capitalize()

                case 'select.list_element':
                    # Select a numbered element of a list (zero indexed)
                    df[params['output']] = _select.list_element(df[params['input']].tolist(), params['parameters']['element'])

                # case 'select.dict_element': placeholder

                case 'select.highest_confidence':
                    # Select the option with the highest confidence. Inputs are expected to be of the form [<<value>>, <<confidence_score>>]
                    df[params['output']] = _select.highest_confidence(df[params['input']].values.tolist())

                case 'select.threshold':
                    # Select the first option if it exceeds a given threshold, else the second option
                    df[params['output']] = _select.confidence_threshold(df[params['input'][0]].tolist(), df[params['input'][1]].tolist(), params['parameters']['threshold'])

                case 'classify':
                    df[params['output']] = _classify(df[params['input']].astype(str).tolist(), **params['parameters'])

                case 'extract.attributes':
                    df[params['output']] = _extract.attributes(df[params['input']].astype(str).tolist())

                case 'extract.properties':
                    df[params['output']] = _extract.properties(df[params['input']].astype(str).tolist())
                
                case 'extract.custom':
                    df[params['output']] = _extract.custom(df[params['input']].astype(str).tolist(), **params['parameters'])
                
                case 'extract.codes':
                    df[params['output']] = _extract.codes(df[params['input']].astype(str).tolist())

                case 'placeholder.common_words':
                    df = df.ww_pd.common_words(params['input'], params['parameters']['subtract'], WordsOnly=True)

                case _:
                    logging.info(f"UNKNOWN WRANGLE :: {wrangle} ::")

    return df


def run(config_file, params={}):
    """
    Execute a YAML defined Wrangling pipeline

    :param config_file: path to a YAML config file
    :param params: (Optional) dictionary of custom parameters to override placeholders in the YAML file 
    """
    logging.info(": Loading Config ::")
    config = _load_config_file(config_file, params)

    logging.info(": Importing Data ::")
    df = _import_file(config['import']['name'], config['import'].get('sheet', 0))

    logging.info(": Running Wrangles ::")
    df = _execute_wrangles(config['wrangles'], df)

    logging.info(": Exporting Data ::")
    df = _export_file(config['export'], df)

    return df