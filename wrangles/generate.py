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

JsonSchemaType = Literal["string", "number", "integer", "boolean", "null", "object", "array"] 

class PropertyDefinition(BaseModel):
    type: JsonSchemaType = "string"
    desccriptions: str
    enum: Optional[List[Any]] = None 
    default: Optional[Any] = None 
    examples: Optional[List[Any]] = None 
    items: Optional[PropertyDefinition] = None 
