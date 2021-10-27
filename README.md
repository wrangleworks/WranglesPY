# WranglesPy

Wrangles python package.

## Installation

### Personal Access Token
Since this is a private repo, to install the package you must generate a personal access token.

 - In Github go to *User Settings -> Develop Settings -> Personal access tokens -> Generate new token*
 - Add *repo scope* and *Generate token*

### Pip

Using the token generated in the first step, install with the following pip command.

```shell
pip install git+https://<token>@github.com/wrangleworks/WranglesPy.git
```

## Usage

```python
>>> import wrangles
>>> wrangles.authenticate('<user>', '<password>') # Alternatively, can be passed as the enviroment variables WRANGLES_USER and WRANGLES_PASSWORD
>>> wrangles.extract.attributes('it is 15mm long')
{'length': ['15mm']}
```

## Wrangles

Wrangles broadly accept a single input string, or a list of strings. If a list is provided, the results will be returned in an equivalent list in the same order and length as the original.

### Classify
```python
# Predict which category an input belongs to
>>> wrangles.classify('ball bearing', 'b7c34bf9-84fe-4fc3')
MechPT

>>> wrangles.classify(['ball bearing', 'spanner'], 'b7c34bf9-84fe-4fc3')
['MechPT', 'Tools']
```

### Data
```python
# Get a list of the user's models
>>> wrangles.data.user.models()
[{'id': '0000f784-ac11-4f8a', 'name': 'Demo Model', 'purpose': 'extract', 'status': 'Ready', 'type': 'user'}, ...]
```

### Extract

#### Attributes
```python
# Extract numeric attributes such as lengths or voltages
>>> wrangles.extract.attributes('it is 15mm long')
{'length': ['15mm']}

>>> wrangles.extract.attributes(['it is 15mm long', 'the voltage is 15V'])
[{'length': ['15mm']}, {'electric potential': ['15V']}]
```

#### Codes
```python
# Extract alphanumeric codes
>>> wrangles.extract.codes('test ABCD1234ZZ test')
['ABCD1234ZZ']

>>> wrangles.extract.codes(['test ABCD1234ZZ test', 'NNN555BBB this one has two XYZ789'])
[['ABCD1234ZZ'], ['NNN555BBB', 'XYZ789']]
```

#### Custom
```python
# Extract entities using a custom model
>>> wrangles.extract.custom('test skf test', '0616f784-ac11-4f8a')
['SKF']

>>> wrangles.extract.custom(['test skf test', 'festo is hidden in here'], '0616f784-ac11-4f8a')
[['SKF'], ['FESTO']]
```
#### Geography
```python
# Extract geographical features such as streets or countries
>>> wrangles.extract.geography('1100 Congress Ave, Austin, TX 78701, USA', 'streets')
['1100 Congress Ave']
```

#### Properties
```python
# Extract categorical properties such as colours or materials
>>> wrangles.extract.properties('yellow submarine')
{'Colours': ['Yellow']}

>>> wrangles.extract.properties(['yellow submarine', 'the green mile'])
[{'Colours': ['Yellow']}, {'Colours': ['Green']}]
```

### Train
```python
# Train a custom classification model
>>> training_data = [
>>>     ['tomato', 'food'],
>>>     ['potato', 'food'],
>>>     ['computer', 'electronics'],
>>>     ['television', 'electronics']
>>> ]
>>> 
>>> name = 'demo model'
>>> 
>>> model_id = wrangles.train.classify(training_data, name)
>>> 
>>> wrangles.classify(['cellphone', 'banana'], model_id)
['electronics', 'food']
```



### Translate
```python
# Translate the input into a different language
>>> wrangles.translate('My name is Chris', 'ES')
Mi nombre es Chris

>>> wrangles.translate(['My name is Chris', 'I live in Austin'], 'DE')
['Mein Name ist Chris', 'Ich wohne in Austin']
```