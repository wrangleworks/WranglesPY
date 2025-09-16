# # wrangles/generate.py 
# from __future__ import annotations 
# import concurrent.futures 
# import json 
# from typing import Any, Dict, List, Literal, Union, Optional 
# from bs4 import BeautifulSoup

# import requests 
# from pydantic import BaseModel, Field, ValidationError 

# # --- Pydantic Models (No changes) --- 
# JsonSchemaType = Literal["string", "number", "integer", "boolean", "null", "object", "array"] 

# class PropertyDefinition(BaseModel): 
#     type: JsonSchemaType = "string" 
#     description: str 
#     enum: Optional[List[Any]] = None 
#     default: Optional[Any] = None 
#     examples: Optional[List[Any]] = None 
#     items: Optional[PropertyDefinition] = None 

# PropertyDefinition.model_rebuild() 

# # --- Helper Function for Web Search --- <<< NEW FUNCTION 
# def _perform_web_search(query: str) -> str: 
#     """ 
#     Performs a simple web search to get context. 
#     NOTE: For production use, a dedicated search API is more robust. 
#     """ 
#     search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}" 
#     headers = { 
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' 
#     } 
#     try: 
#         response = requests.get(search_url, headers=headers, timeout=10) 
#         response.raise_for_status() 
#         soup = BeautifulSoup(response.text, 'html.parser') 
#         snippets = [p.get_text(strip=True) for p in soup.find_all('a', class_='result__a')] 
#         if not snippets: return "No web search results found." 
#         return " ".join(snippets[:5]) 
#     except requests.RequestException: 
#         return "Web search failed." 


# # --- Helper Function - Returns a LIST of results --- 
# def _call_openai( 
#     input_data: Any, api_key: str, payload: dict, url: str, timeout: int, retries: int 
# ) -> dict: 
#     payload['input'] = str(input_data) 
#     headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"} 
#     for attempt in range(retries + 1): 
#         try: 
#             response = requests.post(url, headers=headers, json=payload, timeout=timeout) 
#             response.raise_for_status() 
#             response_json = response.json() 
#             extracted_results = [] 
#             for item in response_json.get('output', []): 
#                 if item.get('type') == 'function_call': 
#                     arguments_str = item.get('arguments') 
#                     if arguments_str: 
#                         result = {"tool_name": item.get('name'), "data": json.loads(arguments_str)} 
#                         extracted_results.append(result) 

#             if not extracted_results: 
#                 return {"error": "Could not find any function calls in the API response.", "raw_response": response_json} 
#             return {"results": extracted_results} 

#         except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError, IndexError) as e: 
#             if attempt >= retries: 
#                 error_details = f"Error: {str(e)}"; 
#                 try: error_details += f" | Response Body: {response.text}" 
#                 except NameError: pass 
#                 return {"error": f"API call failed after {retries + 1} attempts. {error_details}"} 

#     return {"error": "An unexpected error occurred."} 

# # --- Main AI Function - Handles multiple tools --- 
# def ai( 
#     input: Union[Any, List[Any]], 
#     api_key: str, 
#     output: Dict[str, Dict], # Expects a dictionary of named schemas 
#     model: str = "gpt-5", 
#     threads: int = 20, 
#     timeout: int = 90, 
#     retries: int = 0, 
#     messages: Optional[List[dict]] = None, 
#     url: str = "https://api.openai.com/v1/responses", 
#     web_search: bool = False, # <<< ADD THIS
#     reasoning: Dict[str, str] = {"effort": "low"},
#     force_tool: Optional[str] = None, # <<< 1. ADD THIS PARAMETER
#  # <<< ADD THIS
#     **kwargs 
# ) -> Union[dict, list]: 
#     input_was_scalar = not isinstance(input, list) 
#     input_list = [input] if input_was_scalar else input 
#     source_info = "" 
#     system_instructions = "" 

#     if web_search: 
#         source_info = "internet" 
#         search_query = str(input_list[0]) 
#         context = _perform_web_search(search_query) 
#         system_instructions = f""" 
#         You are a helpful assistant. Use ONLY the information from the 'CONTEXT' block below to decide which tool to call and what arguments to provide.

#         CONTEXT:
#         ---
#         {context}
#         ---
#         """ 
#     else: 
#         source_info = "internally generated" 
#         system_instructions = "Analyze the user input and use the provided tools to complete all relevant tasks." 
#         if messages: 
#             system_instructions = messages[0].get('content', system_instructions) 
#     # Build a list of tools from the output dictionary 
#     tools_list = [] 
#     for tool_name, schema_definition in output.items(): 
#         # Validate the properties *inside* each tool's schema 
#         validated_schema_props = {} 
#         try: 
#             for name, definition in schema_definition.items(): 
#                 validated_prop = PropertyDefinition(**definition) 
#                 validated_schema_props[name] = validated_prop.model_dump(exclude_none=True, by_alias=True) 
#         except ValidationError as e: 
#             raise ValueError(f"Invalid schema for tool '{tool_name}': {e}") from e 

#         # Add the fully formed tool to our list 
#         tools_list.append({ 
#             "type": "function", 
#             "name": tool_name, 
#             "description": f"Executes the '{tool_name}' task.", 
#             "parameters": { 
#                 "type": "object", 
#                 "properties": validated_schema_props, 
#                 "required": list(validated_schema_props.keys()) 
#             } 
#         }) 

#     # Assemble the Payload 
#     tool_choice_value: Union[str, Dict] = "auto"
#     if force_tool:
#         if force_tool not in output:
#             raise ValueError(f"Tool '{force_tool}' not found in the defined output schemas.")
#         tool_choice_value = {
#             "type": "function",
#             "function": {"name": force_tool}
#         }

#     payload = { 
#         "model": model, 
#         "instructions": system_instructions, # <<< 6. USES THE DYNAMIC VARIABLE
#         "reasoning": reasoning,             # <<< 7. ADDS THE REASONING KEY
#         "tools": tools_list, 
#         "tool_choice": "auto", 
#         **kwargs 
#     }

#     # Execute and return results 
#     with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor: 
#         # We need to build a new payload for each input, not reuse it 
#         futures = [] 
#         for item in input_list: 
#             # The core payload can be reused, just need to update the input for the helper 
#             # Let's keep the helper function as it is, it handles adding the input. 
#             futures.append(executor.submit(_call_openai, item, api_key, payload, url, timeout, retries)) 
#         results = [future.result() for future in futures] 

#     for res in results: 
#         if isinstance(res, dict) and 'error' not in res: 
#             res['source'] = source_info 

#     if input_was_scalar: 
#         return results[0] 
#     else: 
#         return results
    

# ------------------------------------------



# wrangles/generate.py 
from __future__ import annotations 
import concurrent.futures 
import json 
from typing import Any, Dict, List, Literal, Union, Optional 

import requests 
from bs4 import BeautifulSoup # <<< NEW IMPORT 
from pydantic import BaseModel 

# --- Pydantic Models (No changes) --- 
JsonSchemaType = Literal["string", "number", "integer", "boolean", "null", "object", "array"] 

class PropertyDefinition(BaseModel): 
    type: JsonSchemaType = "string" 
    description: str 
    enum: Optional[List[Any]] = None 
    default: Optional[Any] = None 
    examples: Optional[List[Any]] = None 
    items: Optional[PropertyDefinition] = None 

PropertyDefinition.model_rebuild() 

# --- Helper Function for Web Search --- <<< NEW FUNCTION 
def _perform_web_search(query: str) -> str: 
    """ 
    Performs a simple web search to get context. 
    NOTE: For production use, a dedicated search API is more robust. 
    """ 
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

# --- Helper Function for OpenAI call (No changes) --- 
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

# --- Main AI Function --- 
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

    # <<< --- NEW LOGIC BLOCK --- >>> 
    source_info = "" 
    system_instructions = "" 

    if web_search: 
        source_info = "internet" 
        search_query = str(input_list[0]) # Use the first input item for the search 
        context = _perform_web_search(search_query) 
        system_instructions = f""" 
        You are a helpful assistant. Use ONLY the information from the 'CONTEXT' block below to generate a response that matches the requested JSON schema. 

        CONTEXT: 
        --- 
        {context} 
        --- 
        """ 
    else: 
        source_info = "internally generated" 
        # Use user-provided instructions or a default 
        if messages and isinstance(messages, list) and len(messages) > 0: 
            system_instructions = messages[0].get('content', "Analyze the user input and provide a structured JSON response matching the exact schema provided.") 
        else: 
            system_instructions = "Analyze the user input and provide a structured JSON response matching the exact schema provided." 
    # <<< --- END OF NEW LOGIC BLOCK --- >>> 
    print("arrived to the payload section")
    payload = { 
        "model": model, 
        "instructions": system_instructions, 
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
        futures = [executor.submit(_call_openai, item, api_key, payload, url, timeout, retries) for item in input_list] 

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


