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
