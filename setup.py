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
    description = 'Wrangle your data into shape with AI',
    long_description = long_description,
    long_description_content_type = 'text/markdown',
    license_files = ('LICENSE.txt',),
    license = 'Apache License 2.0',
    classifiers = [
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent'
    ],
    version = '1.11.0',
    url = 'https://github.com/wrangleworks/WranglesPy',
    author = 'WrangleWorks',
    author_email = 'chris@wrangleworks.com',
    keywords = ['data','wrangling'],
    install_requires = requirements,
    entry_points ={
        'console_scripts': ['wrangles.recipe = wrangles.console:recipe']
    },
    project_urls = {
        'Bug Tracker': 'https://github.com/wrangleworks/WranglesPy/issues',
        'Documentation': 'https://wrangles.io/python',
        'Source Code': 'https://github.com/wrangleworks/WranglesPy',
    }
)
