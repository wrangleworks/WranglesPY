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
>>> wrangles.extract.attributes('test 15mmx25mm test')
{'length': ['15mm', '25mm']}
```

## Wrangles

Wrangles broadly accept a single input string, or a list of strings. If a list is provided, the results will be returned in an equivalent list in the same order and length as the original.

### Extract

#### Attributes
Extract numeric attributes such as lengths or voltages.
```python
>>> wrangles.extract.attributes('test 15mmx25mm test')
{'length': ['15mm', '25mm']}
```

#### Codes
Extract alphanumeric codes.
```python
>>> wrangles.extract.codes('test ABCD1234ZZ test')
['ABCD1234ZZ']
```

#### Geography
Extract geographical features such as streets or countries.
```python
>>> wrangles.extract.geography('1100 Congress Ave, Austin, TX 78701, USA', 'streets')
['1100 Congress Ave']
```

#### Properties
Extract categorical properties such as colours or materials.
```python
>>> wrangles.extract.properties('test yellow test')
{'Colours': ['Yellow']}
```