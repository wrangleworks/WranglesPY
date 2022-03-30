from setuptools import setup

setup(
    name='Wrangles',
    packages=['wrangles'],
    description='Wrangle your data into shape with machine learning',
    version='0.2',
    url='https://github.com/wrangleworks/WranglesPy',
    author='Wrangleworks',
    author_email='chris@wrangleworks.com',
    keywords=['data','wrangling'],
    install_requires=['requests', 'pyyaml', 'pandas', 'openpyxl']
)