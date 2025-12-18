import pandas as _pd
from . import recipe_wrangles as _recipe_wrangles
from . import connectors as _connectors


class _wrangles_accessor:
    """
    Used to provide access to wrangle functions.
    """

    def __init__(self, df, wrangle_module):
        self._df = df

        # Add anything not already explicitly defined
        for name in dir(wrangle_module):
            if not name.startswith("_") and not hasattr(self, name):

                def make_method(func_name):
                    target_func = getattr(wrangle_module, func_name)

                    def method(self, *args, **kwargs):
                        self._df.__init__(target_func(self._df, *args, **kwargs))
                        return self._df

                    method.__doc__ = target_func.__doc__
                    return method

                setattr(self, name, make_method(name).__get__(self))

    # Chris attempted to dynaimically source hints but didn't work.
    # Need to document the schema for individual wrangles here (or in spearate file) to get hints at wrangle leve
    # def codes(self, *args, **kwargs):
    #     self._df.__init__(_recipe_wrangles.extract.codes(self._df, *args, **kwargs))
    #     return self._df


# this is alternative syntax.  Not implementing at htis time (Sept'25)
# def codes_alternative(self, output='Column1', *args, **kwargs):
#     return _recipe_wrangles.extract.codes(
#         self._df,
#         input=self._df.columns.tolist(),
#         output=output,
#         *args,
#         **kwargs
#     )[output]


class _wrangles:
    """
    A class to hold wrangles-related methods and properties.
    """

    def __init__(self, df):
        self._df = df

        # Add anything not already explicitly defined
        for name in dir(_recipe_wrangles.main):
            if not name.startswith("_") and not hasattr(self, name):

                def make_method(func_name):
                    target_func = getattr(_recipe_wrangles.main, func_name)

                    def method(self, *args, **kwargs):
                        self._df.__init__(target_func(self._df, *args, **kwargs))
                        return self._df

                    method.__doc__ = target_func.__doc__
                    return method

                setattr(self, name, make_method(name).__get__(self))

    @property
    def compare(self):
        """
        Compare data
        """
        return _wrangles_accessor(self._df, _recipe_wrangles.compare)

    @property
    def convert(self):
        """
        Convert
        """
        return _wrangles_accessor(self._df, _recipe_wrangles.convert)

    @property
    def create(self):
        """
        Create new columns
        """
        return _wrangles_accessor(self._df, _recipe_wrangles.create)

    @property
    def extract(self):
        """
        Wrangles that extract information from the other data,
        such as extract.codes -> get all part codes from descriptions
        """
        return _wrangles_accessor(self._df, _recipe_wrangles.extract)

    @property
    def format(self):
        """
        Format
        """
        return _wrangles_accessor(self._df, _recipe_wrangles.format)

    @property
    def merge(self):
        """
        Merge data together
        """
        return _wrangles_accessor(self._df, _recipe_wrangles.merge)

    @property
    def select(self):
        """
        Select subsets of data
        """
        return _wrangles_accessor(self._df, _recipe_wrangles.select)

    @property
    def split(self):
        """
        Split data apart
        """
        return _wrangles_accessor(self._df, _recipe_wrangles.split)


class _read:
    """
    A class to hold read-related methods and properties.
    """

    def __init__(self, df):
        self._df = df

        # Add anything not already explicitly defined
        for name in dir(_connectors):
            if (
                not name.startswith("_")
                and hasattr(getattr(_connectors, name), "read")
                and not hasattr(self, name)
            ):

                def make_method(func_name):
                    target_func = getattr(getattr(_connectors, func_name), "read")

                    def method(self, *args, **kwargs):
                        self._df.__init__(target_func(*args, **kwargs))
                        return self._df

                    method.__doc__ = target_func.__doc__
                    return method

                setattr(self, name, make_method(name).__get__(self))

    def file(self, name, *args, **kwargs):
        """
        Import a file as defined by user parameters.

        Supports:
        - Excel (.xlsx, .xls, .xlsm)
        - CSV (.csv, .txt)
        - JSON (.json), JSONL (.jsonl)
        - Pickle (.pkl, .pickle) files.

        JSON, JSONL, CSV and Pickle files may also be gzipped (e.g. .csv.gz, .json.gz) and will be decompressed.

        >>> df = wrangles.connectors.file.read('myfile.csv')

        :param name: Name of the file to import
        :return: A Pandas dataframe of the imported data.
        """
        self._df.__init__(_connectors.file.read(name, *args, **kwargs))
        return self._df


class _write:
    """
    A class to hold write-related methods and properties.
    """

    def __init__(self, df):
        self._df = df

        # Add anything not already explicitly defined
        for name in dir(_connectors):
            if (
                not name.startswith("_")
                and hasattr(getattr(_connectors, name), "write")
                and not hasattr(self, name)
            ):

                def make_method(func_name):
                    target_func = getattr(getattr(_connectors, func_name), "write")

                    def method(self, *args, **kwargs):
                        target_func(self._df, *args, **kwargs)

                    method.__doc__ = target_func.__doc__
                    return method

                setattr(self, name, make_method(name).__get__(self))

    def file(self, name: str, *args, **kwargs):
        """
        Output a file to the local file system as defined by the parameters.

        Supports:
        - Excel (.xlsx, .xls)
        - CSV (.csv, .txt)
        - JSON (.json), JSONL (.jsonl)
        - Pickle (.pkl, .pickle)

        JSON, JSONL, CSV and pickle may also be gzipped (e.g. .csv.gz, .json.gz) and will be compressed.

        :param name: Name of the output file
        """
        _connectors.file.write(self._df, name, *args, **kwargs)


class DataFrame(_pd.DataFrame):
    """
    Extends a pandas DataFrame to add wrangles functionality
    """

    @property
    def _constructor(self):
        return DataFrame

    @property
    def read(self):
        """
        Wrangles that read information from the other data,
        such as read.csv -> read a CSV file into a dataframe
        """
        return _read(self)

    @property
    def wrangles(self):
        """
        Apply wrangles to the dataframe
        """
        return _wrangles(self)

    @property
    def write(self):
        """
        Write out the contents of the dataframe to external targets such as files
        """
        return _write(self)
