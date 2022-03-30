
# from readline import write_history_file
import numpy as np
import pandas as pd
import pandas_flavor as pf
from boltons.setutils import IndexedSet 

@pf.register_dataframe_accessor('ww_pd')
class WrangleDf(object):

    def __init__(self, data):
        self._data = data

    def remove_special_chars_colm(self, colm):
        df = self._data
        df[colm] =  df[colm].replace(to_replace=[r"\\t|\\n|\\r|\\r\\n", r'_x000D_',"\t|\n|\r|\r\n"], value=[" "," ", " "], regex=True)
        return df

    def concat_colms(self, colm, colms):
        df = self._data
        df[colm] = df[colms].astype(str).fillna('').agg(' | '.join, axis=1) # astype to ensure no hiccup on data type
        # df[colm] = df[colm].replace(' | ','')
        return df

    def trim_length(self, max_len):
        df = self._data
        df_obj = df.select_dtypes(['object'])
        df[df_obj.columns] = df_obj.astype(str).apply(lambda x: x.str[:max_len])
        return df

# we are taking out anything with numbers, stndalone characters and optionally single letters
    def remove_nonwords(self, colms, suffix):
        df = self._data
        for colm in colms:
            df[colm+suffix] = df[colm]
            df[colm+suffix] = (
                df[colm+suffix] # I added a \ to escape the double quotes to see if that eliminates them. remove if it causes problems
                .str.replace(r'(\w|-|=|/|\'|\")*\d(\w|-|=|/|\'|°|\")*', '', regex=True).fillna('') # words that have one or more digits are matched / removed, or -/ ensure we don't keep internal dividers
                .str.replace(r'(?<!\S).(?!\S)', '', regex=True)# remove all single stand-alone charaters negative look ahead / behind for white space
                .str.replace(r'/', ' / ', regex=True) # put space around any remaining forward slashes
                .str.strip(' |-/*!\#"+')
            )
            # could do spluit and join  to get rid of the extra spaces
            # split would give you the list for other uses later, could add with a flag
            # df[colm+': words'] = (list(df[colm+': words'].values)).str.join(' ')
        return df

# tokenize column, returns tokens colm as list
# List is the way to go. Easy to track & manipulate. Then just rejoin remaining tokens at the end
    def tokenize_colms(self,colms,List=True,Suffix=': tokens'):
        df = self._data
        if Suffix == ': words':
            df = df.ww_pd.remove_nonwords(colms,Suffix)

        for colm in colms:
            split_tokens = df[colm+Suffix].str.split('[." ,:()]+',regex=True)
            if List:
                df[colm+Suffix] = split_tokens
            else: # returns a string version of list which is easier to concatenate
                tkn_string = split_tokens.str.join(',').fillna('') # fill eliminates data type problems with nans
                # TO DO: added something like replace(r'-(?=\w)','') the replace to remove part codes / words preceeded by dash otherwise these don't get subtracted!
                df[colm+Suffix] = (tkn_string)

        return df

# Create vocab from df, subset allows specifying specific tokenized columns
    def create_vocab(self, colm):
        df = self._data
        # iterate through tokens in each row for the series
        _data = pd.Series([x for _list in df[colm] for x in _list]).value_counts()
        # convert series to dataframe to build out all vocab attributes (cnt, spelled, language, case, type)
        vocab = _data.rename_axis('token').to_frame(name='count').reset_index()
        return vocab

# Filter rows of df based on pattern(s) using regex / contains
    def filter_rows_by_patterns(self, patterns: list=[]):
        df = self._data
        pats_joined = "|".join(patterns)
        df_filtered = df[df['token'].str.contains(pats_joined,regex=True)]
        return df_filtered

# Remove redundant / useless tokens from field
    def refine_strings(self, colm):
    # split concatenated fields into strings to remove dupe words / tokens
        df = self._data
        df[colm] = df[colm].str.split(' ')
        for k,v in df.iterrows():
            try:
                df.at[k,colm] = ' '.join(list(dict.fromkeys(v[colm])))
            except:
                pass
        return df

    """ Remove redundant / useless tokens from fieldS
    # old appraoch - do not use
        def remove_dupe_tokens(self, colms):
        # split concatenated fields into strings to remove dupe words / tokens
        # for now just does 1 colm at a time TO DO: multiple colmns
            df = self._data

            # df['all strings'] = df[colms].astype(str).apply(' '.join, axis=1) # joins the strngs from each colm
            df['tokens'] = df[colms].str.split(' |,|;')
            # df = df.wrwx_pd.tokenize_colms(['all strings']) # creates tokens field
            # TO DO: refactor this to use same approach as common words.  Can eliminat iterrows and also list(dict(fromkeys .... by using IndexedSet
            for k,v in df.iterrows():
                try:
                    df.at[k,'final string'] = ' '.join(list(dict.fromkeys(v['tokens'])))
                except:
                    pass
            # df['unique tokens'] = df['unique tokens'].str.replace('\s{2,}', ' ') # replace when more than a single space
            return df
    """

# Function to find and subtract words which are common in colm1 (target) and other colms
# default is to subtract all tokens, not just Wordds, but typically we should remove nonwords first and then subtract yields only core words
    def common_words(self, colm1, colms,WordsOnly=False):
        df = self._data
        if WordsOnly:
            suffix = ': words'
        else:
            suffix = ': tokens'
        # broke out tokenize into separate step for now
        df = df.ww_pd.tokenize_colms([colm1, *colms],List = False,Suffix=suffix)
        colms_tokenized = df.loc[:,df.columns.str.endswith(suffix)]
        # code will contenate first subtract colm with any others
        # it is actually second item in list, the desc colm is first [0]
        df['all to minus'] = colms_tokenized.iloc[:,1].str.cat(colms_tokenized.iloc[:,2:], sep=",")
 
        desc_token_list = df[colm1+suffix].str.split(',')
        minus_token_list = df['all to minus'].str.split(',')
        all_tokens = (zip(desc_token_list, minus_token_list)) # zip joins the two columns into a tuple
        # IndexedSet maintains original sequence which is critical for tokens. It's from Boltons library
        df[colm1+': to remove'] = [list(IndexedSet(a).intersection(IndexedSet(b))) for a, b in all_tokens]
        # have to generate zip second time because it is consumed on first run
        all_tokens = (zip(desc_token_list, minus_token_list))
        # Need to tesdt the statement below, I'm not sure why doing set on B.  Maybe works either way
        df[colm1+': minused'] = [list(IndexedSet(a).difference(b)) for a, b in all_tokens]
        df[colm1+' core words'] = df[colm1+': minused'].str.join(' ').str.strip(' |-/*!\#=') # second strip removes chars that get revealed after the intersect
        return df


# TODO Not working yet...
    def remove_nans(self, colm):
        df = self._data
        df[colm] = df[colm].fillna('') # should empty the excel cell that otherwise would be nan
        return df

    def extract_content(self, colm, rgx):
        df = self._data
        df[colm+'_extract'] = df[colm].str.extract(rgx)
        return df
