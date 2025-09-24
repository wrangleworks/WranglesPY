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

PropertyDefinition.model_rebuild()

def _perform_web_search(query: str) -> str: 
    """Perform a simple web search to get context via DuckDuckGo."""
    if BeautifulSoup is None:
        return "Web search unavailable because beautifulsoup4 is not installed."

    search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}" 
    headers = { 
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' 
    } 
    try: 
        response = requests.get(search_url, headers=headers, timeout=10) 
        response.raise_for_status() 
        soup = BeautifulSoup(response.text, 'html.parser') 
        snippets = [p.get_text(strip=True) for p in soup.find_all('a', class_='result__a')] 
        if not snippets: return "No web search results found." 
        return " ".join(snippets[:5]) 
    except requests.RequestException: 
        return "Web search failed." 


def _stringify_query(record: Any) -> str:
    """Create a search query string from an arbitrary record."""
    if isinstance(record, dict):
        return " ".join(str(v) for v in record.values() if v not in (None, ""))
    if isinstance(record, list):
        return " ".join(str(v) for v in record if v not in (None, ""))
    if record in (None, ""):
        return ""
    return str(record)



def _call_openai( 
    input_data: Any, api_key: str, payload: dict, url: str, timeout: int, retries: int 
) -> dict: 
    print("arrived to the openai section")
    # This function remains the same as your version 
    payload_copy = payload.copy()
    payload_copy['input'] = str(input_data) # Modify the copy, not the original
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"} 
    for attempt in range(retries + 1): 
        try: 
            response = requests.post(url, headers=headers, json=payload_copy, timeout=timeout) 
            print(f">>> API Request Payload: {json.dumps(payload_copy, indent=2)}")
            response.raise_for_status() 
            response_json = response.json() 
            # ---
            print(f">>> API Status Code: {response.status_code}")
            print(f">>> API Response Text: {response.text}")
            # ---

            for item in response_json.get('output', []): 
                if item.get('type') == 'message': 
                    content = item.get('content', []) 
                    if content and content[0].get('type') == 'output_text': 
                        json_string = content[0].get('text') 
                        return json.loads(json_string) 
            return {"error": "Could not find 'output_text' in the API response.", "raw_response": response_json} 
        except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError, IndexError) as e: 
            if attempt >= retries: 
                error_details = f"Error: {str(e)}"; 
                try: error_details += f" | Response Body: {response.text}" 
                except NameError: pass 
                return {"error": f"API call failed after {retries + 1} attempts. {error_details}"} 
    return {"error": "An unexpected error occurred."} 
