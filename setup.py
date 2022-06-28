from setuptools import setup

# read the contents of the README file
from pathlib import Path
long_description = (Path(__file__).parent / "README.md").read_text()

setup(
    name = 'wrangles',
    packages = [
        'wrangles',
        'wrangles.connectors',
        'wrangles.recipe_wrangles'
    ],
    description = 'Wrangle your data into shape with machine learning',
    long_description = long_description,
    long_description_content_type = 'text/markdown',
    version = '0.4',
    url = 'https://wrangles.io',
    author = 'WrangleWorks',
    author_email = 'chris@wrangleworks.com',
    keywords = ['data','wrangling'],
    install_requires = [
        'requests',
        'pyyaml',
        'pandas',
        'openpyxl',
        'sqlalchemy',
        'pymssql',
        'psycopg2-binary',
        'pymysql',
        'fabric',
        'apprise',
        'lorem',
        'pymongo[srv]',
        'simple-salesforce'
    ]
)