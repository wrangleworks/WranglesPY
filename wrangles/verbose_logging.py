from jinja2 import (
    Environment as _Environment,
    BaseLoader as _BaseLoader
)
import copy as _copy
import logging as _logging
import pandas as _pd

# This is moved here as the earlier file based method will not work
# when the code is deployed as a package.
template_jinja = """
{# Test against cases where multipe i/o's are used against a single i/o #}
{% if data.read %}
## Read
This recipe first reads in a {% for key, value in data.read[0].items() %} **{{ key }}** with the filepath *{{ variables['inputFile'] }}* and a length of {% if logs %}**{{ (logs[0]['dfWrangled']|length) }} {% endif %} rows**. {% endfor %}

  - Additional parameters: {{ read_params }}
{% endif %}

{% if data.wrangles %}
## Wrangles
{% for i in range((logs|length)) %}
    {% set outer_loop = loop %}

{{outer_loop.index}}. **{{ wrangles[i] }}** *{{ logs[i]['wrangle'][wrangles[i]]['input'] }}* into {% if logs[i]['wrangle'][wrangles[i]]['output'] is defined %} *{{ logs[i]['wrangle'][wrangles[i]]['output'] }}* {% else %} *{{ logs[i]['wrangle'][wrangles[i]]['input'] }}* (the column name was not changed) {% endif %}
  {% if logs[i]['otherParameters'] is defined %}
  - Additional parameters: {% for key, value in logs[i]['otherParameters'].items() %} 
    - {{ key }}: {{ value }}
  {% endfor %}
  {% endif %}
{% if not logs[i]['dfRaw'].empty %} 
  - Before:

    | {% for column in logs[i]['dfRaw'].columns %} {{ column }} | {% endfor %}
    | {% for j in range((logs[i]['dfRaw'].columns|length)) %} ----| {% endfor %}
    | {% for j in range((logs[i]['dfRaw'].columns|length)) %} | {% endfor %} {% for k in range(5) %}
    | {% for column in logs[i]['dfRaw'].columns %} {{ logs[i]['dfRaw'][column][k] }} | {% endfor %} {% endfor %}
    |  |  |  |  |
    {% endif %}

{% if not logs[i]['dfWrangled'].empty %} 
  - After:

    | {% for column in logs[i]['dfWrangled'].columns %} {{ column }} | {% endfor %}
    | {% for j in range((logs[i]['dfWrangled'].columns|length)) %} ----| {% endfor %}
    | {% for j in range((logs[i]['dfWrangled'].columns|length)) %} | {% endfor %} {% for k in range(5) %}
    | {% for column in logs[i]['dfWrangled'].columns %} {{ logs[i]['dfWrangled'][column][k] }} | {% endfor %} {% endfor %}
    |  |  |  |  |
    {% endif %}

    {% endfor %}

{% endif %}

{% if data.write %}
## Write

The recipe writes to a {% for key, value in data.write[0].items() %} **{{ key }}** {% if variables['outputFile'] %} with a filepath/name of *{{ variables['outputFile'] }}* {% endif %} with the following parameters:

  - Columns: {% for column in value.columns %}
     - {{ column }}
     {% endfor %}
  
  {% for params in write_params %} {% if params|length > 0 %}- Additional parameters: {{ params }} {% endif %} {% endfor %}
{% endfor %}
{% endif %}
"""

class MyFilter(object):
    def __init__(self, level):
        self.__level = level

    def filter(self, logRecord):
        return logRecord.levelno == self.__level

class ProgressConsoleHandler(_logging.StreamHandler):
    """
    A handler class which allows the cursor to stay on
    one line for selected messages
    """
    
    def __init__(self):
        super().__init__()
        self.logging_record = []
        self.log_file = None
        self.wrangles = []
        self.recipe = None
        self.df = _pd.DataFrame()
        self.readParameters = []
        self.writeParameters = []

    # on_same_line = False
    def emit(self, record):
        """
        Builds records of each wrangle
        :param self: Allows access to the attributes and methods of the ProgressConsoleHandler Class
        :param record: The information passed in the logger. Contains log message, dataframe, wrangles, recipes etc
        """
        if record.msg:
            print(record.msg)
            if record.msg[-16:] == 'rows imported ::':
            # if 'read' in record.args:
                self.df = record.args[0]
        try:
            if record.args[2] == 'wrangle' and list(record.args[1].items())[0][0] != 'log':
                try: self.input = record.args[1][list(record.args[1].items())[0][0]]['input']
                except: self.input = None
                try: self.output = record.args[1][list(record.args[1].items())[0][0]]['output']
                except: self.output = self.input
                if list(record.args[1].items())[0][0] == 'math' or list(record.args[1].items())[0][0] == 'maths':
                    self.input = None
                wrangled = record.args[0]
                raw, wrangled = self._compare_df(wrangled)
                self.logging_record.append({'wrangle': record.args[1], 'dfWrangled': wrangled, 'dfRaw': raw})
                self.df = record.args[0]
        except:
            pass
        record.args = None

    def _compare_df(self, wrangled):
        """
        Compares before and after dataframes to come up with the differences
        :param self: Allows access to the attributes and methods of the ProgressConsoleHandler Class
        :param wrangled: The 'Wrangled' or 'after' dataframe, used to compare to previous version ('before')
        """
        # Find common columns
        common_cols = list(set(self.df.columns) & set(wrangled.columns))

        # Compare overlapping columns
        self.df_common = self.df[common_cols]
        wrangled_common = wrangled[common_cols]
        diff_common = []
        for col in common_cols:
            if self.df_common[col].equals(wrangled_common[col]) == False:
                diff_common.append(col)

        # Find differing columns
        self.df_only_cols = list(set(self.df.columns) - set(wrangled.columns))
        wrangled_only_cols = list(set(wrangled.columns) - set(self.df.columns))

        wrangled = wrangled[diff_common + wrangled_only_cols]
        raw = self.df[diff_common + self.df_only_cols]
        if raw.empty:
            try:
                raw = _pd.DataFrame(self.df[self.input])
            except:
                raw = self.df

        # Drop rows which have not been affected by the wrangle
        dropList = []
        if self.input:
            try:
                test1 = raw[self.input].isin(wrangled[self.output])
            except:
                test1 = raw[self.input].isin(wrangled)
        test2 = raw.isin(wrangled)
        for i in range(len(raw)):
            try:
                if test1[i] == True:
                    dropList.append(i)
            except:
                if test2.iloc[i][0] == True:
                    dropList.append(i)
        
        raw = raw.drop(dropList).reset_index(drop=True)
        wrangled = wrangled.drop(dropList).reset_index(drop=True)
        return raw, wrangled

    def _read_params(self):
        """
        Appends self.readParameters with all parameters, except name, from the read
        :param self: allows access to the attributes and methods of the ProgressConsoleHandler Class
        """
        try:
            for wrangle in self.recipe['read']:
                for key, value in wrangle.items():
                    values = list(value)
                    for k in values:
                        if k == 'name':
                            del value[k]
                    self.readParameters.append(value)
        except:
            pass


    def _write_params(self):
        """
        Appends self.readParameters with all parameters, except columns and name, from the write
        :param self: allows access to the attributes and methods of the ProgressConsoleHandler Class
        """
        if 'write' in self.recipe:
            temp = _copy.deepcopy(self.recipe)
            for wrangle in temp['write']:
                for key, value in wrangle.items():
                    values = list(value)
                    for k in values:
                        if k == 'columns':
                            del value[k]
                        if k == 'name':
                            del value[k]
                    self.writeParameters.append(value)

    def _otherParams(self, i):
        """
        Creates a dictionary entry in logging_record that consists of any parameters other than 
        input, output, and model_id.
        :param self: allows access to the attributes and methods of the ProgressConsoleHandler Class
        :param i: used as an index for logging_record
        """
        otherParameters = _copy.deepcopy(self.logging_record[i]['wrangle'][self.wrangles[i]])
        keys = list(otherParameters.keys())
        for key in keys:
            if key == 'input':
                del otherParameters[key]
            if key == 'output':
                del otherParameters[key]
            if key == 'model_id':
                del otherParameters[key]
        if len(otherParameters) > 0:
            self.logging_record[i]['otherParameters'] = otherParameters


    def create_log(self, recipe, variables, log_file):
        '''
        Uses jinja2 to create documentation for any recipe, based on template.md

        :param df: The output dataframe of the recipe being ran
        :param recipe: A dictionary representation of the recipe
        :param variables: The variables list defined in the python run file for the recipe being ran
        :param log_file: Takes in the specified file path of the log to be created
        '''
        self.recipe = recipe
        self.log_file = log_file
        self._read_params()
        self._write_params()
        self.template = _Environment(loader=_BaseLoader).from_string(template_jinja)
        for i in range(len(self.logging_record)):
            self.wrangles.append(list(self.logging_record[i]['wrangle'].items())[0][0])
            self._otherParams(i)

        results_filename = self.log_file

        context = {
            "data": recipe,
            "logs": self.logging_record,
            "variables": variables,
            "read_params": self.readParameters,
            "write_params": self.writeParameters,
            'wrangles': self.wrangles
        }
        
        with open(results_filename, mode="w", encoding="utf-8") as results:
            results.write(self.template.render(context))
            print(f"... wrote {results_filename}")

