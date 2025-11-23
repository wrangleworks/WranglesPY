from __future__ import annotations
import concurrent.futures
import copy
import json
from typing import Any, Dict, List, Literal, Union, Optional, Tuple

import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from pydantic import BaseModel

JsonSchemaType = Literal["string", "number", "integer", "boolean", "null", "object", "array"]

class PropertyDefinition(BaseModel):
   
    type: JsonSchemaType = "string"
    description: str
    enum: Optional[List[Any]] = None
    default: Optional[Any] = None
    examples: Optional[List[Any]] = None
    items: Optional["PropertyDefinition"] = None

PropertyDefinition.model_rebuild()


def _perform_web_search(query: str) -> str:
    if BeautifulSoup is None:
        return "Web search unavailable because beautifulsoup4 is not installed."

    search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/91.0.4472.124 Safari/537.36'
        )
    }
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        snippets = [a.get_text(strip=True) for a in soup.find_all('a', class_='result__a')]
        if not snippets:
            return "No web search results found."
        return " ".join(snippets[:5])
    except requests.RequestException:
        return "Web search failed."


def _stringify_query(record: Any) -> str:
    
    if isinstance(record, dict):
        return " ".join(str(v) for v in record.values() if v not in (None, ""))
    if isinstance(record, list):
        return " ".join(str(v) for v in record if v not in (None, ""))
    if record in (None, ""):
        return ""
    return str(record)


def _call_openai(
    input_data: Any,
    api_key: str,
    payload: dict,
    url: str,
    timeout: int,
    retries: int,
    previous_response_id: Optional[str] = None
) -> Tuple[dict, Optional[str]]:
    payload_copy = payload.copy()
    if "input" not in payload_copy:
        payload_copy["input"] = str(input_data)
    if previous_response_id:
        payload_copy["previous_response_id"] = previous_response_id
    elif "previous_response_id" in payload_copy:
        payload_copy.pop("previous_response_id")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    for attempt in range(retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload_copy, timeout=timeout)
            response.raise_for_status()
            response_json = response.json()
            response_id = response_json.get("id")
            
            for item in response_json.get("output", []):
                if item.get("type") == "message":
                    content = item.get("content", [])
                    if content and content[0].get("type") == "output_text":
                        json_string = content[0].get("text")
                        parsed = json.loads(json_string)

                        summary_blocks = response_json.get("summary")
                        if not summary_blocks:
                            for block in response_json.get("output", []):
                                summary_blocks = block.get("summary")
                                if summary_blocks:
                                    break

                        if summary_blocks:
                            summary_text = "".join(
                                part.get("text", "")
                                for part in summary_blocks
                                if isinstance(part, dict) and part.get("type") == "summary_text"
                            )
                            if summary_text:
                                if isinstance(parsed, dict):
                                    parsed["summary"] = summary_text
                                elif isinstance(parsed, list):
                                    for entry in parsed:
                                        if isinstance(entry, dict):
                                            entry["summary"] = summary_text

                        return parsed, response_id

            return (
                {"error": "Could not find 'output_text' in the API response.", "raw_response": response_json},
                None,
            )
        except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError, IndexError) as e:
            if attempt >= retries:
                error_details = f"Error: {str(e)}"
                try:
                    error_details += f" | Response Body: {response.text}"
                except NameError:
                    pass
                return ({"error": f"API call failed after {retries + 1} attempts. {error_details}"}, None)

    return ({"error": "An unexpected error occurred."}, None)


def ai(
    input: Union[Any, List[Any]],
    api_key: str,
    output: Dict[str, Any],
    model: str = "gpt-5-mini",
    threads: int = 20,
    timeout: int = 90,
    retries: int = 0,
    messages: Optional[List[dict]] = None,
    url: str = "https://api.openai.com/v1/responses",
    strict: bool = True,
    web_search: bool = False,
    reasoning: Dict[str, str] = {"effort": "low"},
    previous_response: bool = False,  
    examples: Optional[List[Dict[str, Any]]] = None,
    summary: bool = False,
    **kwargs
) -> Union[dict, list]:
    """
    type: object
    description: Generate structured AI output for each recipe row.
    additionalProperties: false
    required:
      - api_key
      - output
    properties:
      api_key:
        type: string
        description: OpenAI-compatible API key.
      input:
        type:
          - string
          - array
        description: Column(s) to concatenate into the prompt (defaults to all columns).
      output:
        type:
          - string
          - object
          - array
        description: Target schema; string/array shorthands are expanded automatically.
      model:
        type: string
        description: Responses model name (e.g. gpt-5-mini).
      threads:
        type: integer
        description: Maximum concurrent requests (default 20).
      timeout:
        type: integer
        description: Per-request timeout in seconds.
      retries:
        type: integer
        description: Number of retry attempts on failure.
      messages:
        type: array
        description: Optional extra messages forwarded to the inner generate helper.
      url:
        type: string
        description: Override for the OpenAI-compatible endpoint.
      strict:
        type: boolean
        description: Enforce JSON-schema validation on the response.
      web_search:
        type: boolean
        description: Enable DuckDuckGo context lookup per row.
      reasoning:
        type: object
        description: Responses API reasoning options (forwarded verbatim).
      previous_response:
        type: boolean
        description: Chain responses by reusing previous_response_id for field-by-field calls.
      summary:
        type: boolean
        description: Request summary text to be merged into the output.
    """

    input_was_scalar = not isinstance(input, list)
    input_list = [input] if input_was_scalar else input

    properties = output.get("properties", {}) if isinstance(output, dict) else {}
    property_order = list(properties.keys())

    field_summaries: List[str] = []
    for name, details in properties.items():
        if isinstance(details, dict):
            field_type = details.get("type", "string")
            description = details.get("description", "No description supplied.")
        else:
            field_type = "string"
            description = str(details)
        field_summaries.append(f"- `{name}`: type `{field_type}` — {description}")

    schema_requirements = "\n".join(field_summaries) if field_summaries else "- No structured fields provided."

    if previous_response:
        base_instruction = (
            "SYSTEM ROLE: You are a structured-output assistant continuing a chained generation.\n"
            "PRIMARY OBJECTIVE: Generate the next JSON fields so they satisfy the requested schema while staying "
            "consistent with prior responses maintained by the API.\n"
            "SCHEMA REQUIREMENTS:\n"
            f"{schema_requirements}\n"
            "STRICT RULES:\n"
            "- Use only the RECORD DATA together with any earlier model responses supplied by the API.\n"
            "- Never contradict existing outputs; when information is missing, respond with \"N/A\".\n"
            "- Return valid JSON matching the schema exactly—no explanations or extra keys."
            "- Always select the most relevant example from the provided few-shot examples, and strictly follow the guidance in the associated notes if they are present."
        )
    else:
        base_instruction = (
            "SYSTEM ROLE: You are a structured-output assistant.\n"
            "PRIMARY OBJECTIVE: Generate a complete JSON object that satisfies the requested schema using only the provided data.\n"
            "SCHEMA REQUIREMENTS:\n"
            f"{schema_requirements}\n"
            "STRICT RULES:\n"
            "- Use only the RECORD DATA. Do not invent or infer missing values.\n"
            "- When information is unavailable, respond with \"N/A\".\n"
            "- Return valid JSON matching the schema exactly—no explanations or extra keys."
            "- Always select the most relevant example from the provided few-shot examples, and strictly follow the guidance in the associated notes if they are present."
        )

    if messages and isinstance(messages, list) and len(messages) > 0:
        base_instruction = messages[0].get('content', base_instruction)

    contexts: List[Optional[str]] = []
    if web_search:
        source_info = "internet"
        for item in input_list:
            context = _perform_web_search(_stringify_query(item))
            contexts.append(context)
    else:
        source_info = "input"
        contexts = [None for _ in input_list]
    if summary:
        reasoning['summary'] = 'auto'
    else:
        reasoning = reasoning

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

    example_pairs: List[Tuple[Any, Any]] = []

    if examples and isinstance(examples, list):
        for example in examples:
            example_input = example.get("input")
            example_output = example.get("output")
            if example_input is None or example_output is None:
                continue

            cleaned_input = example_input
            if example.get('notes'):
                cleaned_input = {"input": cleaned_input, "notes": example["notes"]}

            pair = (cleaned_input, example_output)   
            example_pairs.append(pair)


    def _build_messages(
        example_pairs_local: List[Tuple[Any, Any]],
        item_local: Any,
        context_local: Optional[str]
    ) -> List[Dict[str, str]]:
        msgs: List[Dict[str, str]] = []
        if context_local:
            msgs.append({"role": "user", "content": f"ADDITIONAL CONTEXT:\n---\n{context_local}\n---"})

        for ex_inp, ex_out in example_pairs_local:
            in_str = ex_inp if isinstance(ex_inp, str) else json.dumps(ex_inp, ensure_ascii=False)
            out_str = ex_out if isinstance(ex_out, str) else json.dumps(ex_out, ensure_ascii=False)
            msgs.append({"role": "user", "content": in_str})
            msgs.append({"role": "assistant", "content": out_str})

        msgs.append({"role": "user", "content": json.dumps(item_local, ensure_ascii=False)})

        return msgs

    def _generate_record(item: Any, context: Optional[str]) -> Dict[str, Any]:
        payload = copy.deepcopy(payload_template)
        payload["instructions"] = base_instruction
        payload["input"] = _build_messages(example_pairs, item, context)

        record, _ = _call_openai(
            None,
            api_key,
            payload,
            url,
            timeout,
            retries,
        )
        return record
    

    def _generate_record_by_field(item: Any, context: Optional[str]) -> Dict[str, Any]:
        response_id: Optional[str] = None
        combined: Dict[str, Any] = {}

        for field_name in properties.keys():
            field_schema = {
                "type": "object",
                "properties": {field_name: properties[field_name]},
                "required": [field_name],
                "additionalProperties": False
            }

            msgs = _build_messages(example_pairs, item, context)

            payload = copy.deepcopy(payload_template)
            payload["instructions"] = base_instruction
            payload["input"] = msgs
            payload["text"]["format"]["schema"] = field_schema

            rec, response_id = _call_openai(
                None,
                api_key,
                payload,
                url,
                timeout,
                retries,
                
                previous_response_id=response_id,
            )

            if isinstance(rec, dict) and "error" in rec:
                return rec

            if isinstance(rec, dict):
                combined.update(rec)
            else:
                combined[field_name] = rec

            if response_id is None:
                break

        return combined

    
    generate_fn = _generate_record_by_field if previous_response else _generate_record

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [
            executor.submit(generate_fn, item, context)
            for item, context in zip(input_list, contexts)
        ]
        results = [future.result() for future in futures]

    for res in results:
        if isinstance(res, dict) and 'error' not in res:
            res['source'] = source_info

    return results[0] if input_was_scalar else results
