from setuptools import setup

setup(
    name = 'wrangles',
    packages = [
        'wrangles',
        'wrangles.connectors',
        'wrangles.match',
        'wrangles.pipeline_wrangles'
    ],
    description = 'Wrangle your data into shape with machine learning',
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
        'pyodbc',
        'sqlalchemy',
        'pymssql',
        'psycopg2-binary',
        'pymysql',
        'fabric',
        'apprise',
        'lorem',
        'pymongo[srv]'
    ]
)