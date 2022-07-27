from setuptools import setup

# read the contents of the README file
from pathlib import Path
long_description = (Path(__file__).parent / "README.md").read_text()

# Get the contents of the requirements file
with open('requirements.txt') as f:
    requirements = f.readlines()

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
    version = '0.5',
    url = 'https://wrangles.io',
    author = 'WrangleWorks',
    author_email = 'chris@wrangleworks.com',
    keywords = ['data','wrangling'],
    install_requires = requirements,
    entry_points ={
        'console_scripts': ['wrangles.recipe = wrangles.console:recipe']
    },
)