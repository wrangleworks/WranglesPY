from __future__ import annotations
import concurrent.futures
import copy
import json
from typing import Any,Dict,List,Literal,Union,Optional

import requests
try:
    from bs4 import BeautifulSoup

except ImportError:
    BeautifulSoup = None 

from pydantic import BaseModel

