from setuptools import setup

setup(
    name = 'wrangles',
    packages = ['wrangles', 'wrangles.match', 'wrangles.connectors'],
    description = 'Wrangle your data into shape with machine learning',
    version = '0.2.3',
    url = 'https://github.com/wrangleworks/WranglesPy',
    author = 'Wrangleworks',
    author_email = 'chris@wrangleworks.com',
    keywords = ['data','wrangling'],
    install_requires = [
        'requests',
        'pyyaml',
        'pandas',
        'openpyxl',
        'pandas_flavor',
        'boltons',
        'pyodbc',
        'sqlalchemy',
        'pymssql',
        'psycopg2-binary'
    ]
)