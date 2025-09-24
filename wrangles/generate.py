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


def ai( 
    input: Union[Any, List[Any]], 
    api_key: str, 
    output: Dict[str, Any], 
    model: str = "gpt-5", 
    threads: int = 20, 
    timeout: int = 90, 
    retries: int = 0, 
    messages: Optional[List[dict]] = None, 
    url: str = "https://api.openai.com/v1/responses", 
    strict: bool = False, 
    web_search: bool = False, # <<< NEW PARAMETER 
    reasoning: Dict[str, str] = {"effort": "low"}, 
    **kwargs 
) -> Union[dict, list]: 
    print("process has started")
    print(f"web_search is set to: {web_search}, strict is set to: {strict}")
    input_was_scalar = not isinstance(input, list) 
    input_list = [input] if input_was_scalar else input 

    default_instruction = (
        "You are an assistant that MUST rely solely on the values contained in the current record. "
        "Do not use outside knowledge, do not invent details, and respond with 'N/A' when information is missing. "
        "Return JSON that matches the requested schema exactly."
    )
    if messages and isinstance(messages, list) and len(messages) > 0:
        default_instruction = messages[0].get('content', default_instruction)

    compliance_notice = (
        "\n\nRESTRICTIONS:\n"
        "- Only use data from the supplied RECORD DATA.\n"
        "- Never fabricate or infer information that is not present.\n"
        "- Use 'N/A' when the record lacks the requested value."
    )

    if web_search:
        source_info = "internet"
        instructions_by_item = []
        for item in input_list:
            context = _perform_web_search(_stringify_query(item))
            instructions_by_item.append(
                "You are a helpful assistant. Use ONLY the information from the 'CONTEXT' block below to generate a response that matches the requested JSON schema.\n\n"
                "CONTEXT:\n---\n"
                f"{context}\n---"
            )
    else:
        source_info = "internally generated"
        instructions_by_item = []
        for item in input_list:
            record_context = json.dumps(item, ensure_ascii=False)
            instructions_by_item.append(
                f"{default_instruction}{compliance_notice}\n\nRECORD DATA:\n---\n{record_context}\n---"
            )

    print("arrived to the payload section")
    payload_template = {
        "model": model,
        "reasoning": reasoning,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "structured_response",
                "schema": output,
                "strict": strict
            }
        },
        **kwargs
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for item, instructions in zip(input_list, instructions_by_item):
            payload = copy.deepcopy(payload_template)
            payload["instructions"] = instructions
            futures.append(executor.submit(_call_openai, item, api_key, payload, url, timeout, retries))

        results = [future.result() for future in futures] 
        print(f"arrived to the results section{results}")
    # <<< NEW: Add source information to results --- >>> 
    for res in results: 
        if isinstance(res, dict) and 'error' not in res: 
            res['source'] = source_info 

    if input_was_scalar: 
        return results[0] 
    else: 
        return results
