import wrangles


# Data
def test_user_models():
    result = wrangles.data.user.models('extract')
    assert len(result) > 0

def test_user_models_extract():
    result = wrangles.data.user.models('extract')
    assert result[0]['purpose'] == 'extract'

def test_user_models_classify():
    result = wrangles.data.user.models('classify')
    assert result[0]['purpose'] == 'classify'

# Extract
def test_attributes():
    result = wrangles.extract.attributes('something 15V something')
    assert result['electric potential'][0] == '15V'

def test_attributes_list():
    result = wrangles.extract.attributes(['something 15V something'])
    assert result[0]['electric potential'][0] == '15V'

def test_codes():
    result = wrangles.extract.codes('something ABC123ZZ something')
    assert result[0] == 'ABC123ZZ'

def test_codes_list():
    result = wrangles.extract.codes(['something ABC123ZZ something'])
    assert result[0][0] == 'ABC123ZZ'

def test_geography():
    result = wrangles.extract.geography('1100 Congress Ave, Austin, TX 78701, USA', 'streets')
    assert result[0] == '1100 Congress Ave'

def test_geography_list():
    result = wrangles.extract.geography(['1100 Congress Ave, Austin, TX 78701, USA'], 'streets')
    assert result[0][0] == '1100 Congress Ave'

def test_properties():
    result = wrangles.extract.properties('something yellow something')
    assert result['Colours'][0] == 'Yellow'

def test_properties_list():
    result = wrangles.extract.properties(['something yellow something'])
    assert result[0]['Colours'][0] == 'Yellow'


# Translate
def test_translate():
    result = wrangles.translate('My name is Chris', 'DE')
    assert result == 'Mein Name ist Chris'

def test_translate_list():
    result = wrangles.translate(['My name is Chris'], 'DE')
    assert result[0] == 'Mein Name ist Chris'