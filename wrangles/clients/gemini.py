import asyncio
import concurrent.futures
import math
import os
from typing import Optional, Dict, Any
from ..utils import LazyLoader as _LazyLoader
from .. import ai_config as _ai_config

# Lazy-loaded Google GenAI modules
genai = _LazyLoader("google.genai")
types = _LazyLoader("google.genai.types")
errors = _LazyLoader("google.genai.errors")
_httpx = _LazyLoader("httpx")

def _get_genai():
    """
    Lazy loader for Google GenAI SDK to prevent hard dependencies.

    The actual imports will not occur until one of the returned
    modules is first accessed.
    """
    return genai, types, errors

class GeminiURLContextClient:
    DEFAULT_SYSTEM_PROMPT = """
    You are a product research assistant. 
    Your job is to read product pages and extract specific technical data.

    Output Rules:
    - If info is missing, write "Not Found".
    - Generate a unique summary for Description (do not recite).

    Required Sections:
    ## Product: the official product name / title.
    ## Brand: the product brand or manufacturer.
    ## IDs: list of Part Numbers, SKUs, UPC, MPN, etc.
    ## Category: the product category breadcrumb.
    ## Description: summary text describing key features.
    ## Specs: list of specifications and features.
    ## Pricing: pricing information including currency.
    ## Metadata: list of page title, description, and keywords.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.genai, self.types, self.errors = _get_genai()
        
        # Save the key without instantiating the Client.
        # This allows each thread to create its own Client later for thread safety.
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Missing API Key: Provide `api_key` in the recipe config or set the GOOGLE_API_KEY environment variable."
            )

    def retrieve(self, url: str, prompt: Optional[str] = None, model_id: str = None,
                 output_format: str = "markdown", thinking_level: str = None,
                 request_timeout_seconds: float = None, **kwargs) -> Dict[str, Any]:
        """
        Retrieves context from a web URL using the Gemini API.
        Includes thread-safe initialization, strict timeouts, and optional JSON parsing.
        """
        policy = None
        if url and str(url).strip():
            policy = _ai_config.resolve("search.retrieve_link_content", model=model_id)
            if thinking_level is not None:
                policy["thinking_level"] = thinking_level
            if request_timeout_seconds is not None:
                policy["request_timeout_seconds"] = request_timeout_seconds
            _ai_config.warn_if_deprecated(policy["model"], policy["provider"])
        return self._retrieve(url, prompt, output_format, policy, **kwargs)

    @staticmethod
    def _generate_with_deadline(client, timeout, **request):
        """Cancel the whole SDK request, including retries, before closing it."""
        async def generate():
            try:
                return await asyncio.wait_for(
                    client.aio.models.generate_content(**request), timeout=timeout,
                )
            finally:
                await client.aio.aclose()

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(generate())
        # The public client remains usable from synchronous code inside an
        # existing event loop, without attempting to nest asyncio.run().
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(generate())).result()

    def _retrieve(self, url, prompt, output_format, policy, **kwargs):
        """Retrieve one URL using the operation's already resolved policy."""
        result = {
            "retrieved_url": url, 
            "status": "Failure",
            "error": None,
            "extracted_content": None
        }

        if not url or str(url).strip() == "":
            result["error"] = "Skipped: URL is missing or empty"
            return result
            
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
            result["retrieved_url"] = url

        if policy["provider"] != "google":
            raise ValueError("URL content retrieval currently supports only the 'google' provider.")
        if policy["protocol"] != "generate_content":
            raise ValueError("Google URL content retrieval requires the 'generate_content' protocol.")
        model_id = policy["model"]
        timeout = policy["request_timeout_seconds"]
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("request_timeout_seconds must be a positive finite number.")
        thinking_level = policy.get("thinking_level")
        if thinking_level is not None and thinking_level not in ("minimal", "low", "medium", "high"):
            raise ValueError("thinking_level must be minimal, low, medium, or high.")
        reserved = {
            "system_instruction", "systemInstruction", "tools",
            "response_mime_type", "responseMimeType", "response_modalities", "responseModalities",
            "http_options", "httpOptions",
        }
        if reserved.intersection(kwargs):
            names = ", ".join(sorted(reserved.intersection(kwargs)))
            raise ValueError(f"Retrieval manages {names}; use prompt, output_format, or request_timeout_seconds instead.")
            
        user_content = f"Please retrieve content from this explicitly bounded URL: <{url}>"

        base_prompt = prompt if prompt else self.DEFAULT_SYSTEM_PROMPT

        # Format-specific prompting
        if output_format.lower() == "json":
            system_instruction = base_prompt + "\n\nCRITICAL FORMAT RULE:\n- You must return the requested sections as a strictly valid JSON object where the section names are the keys."
            mime_type = "application/json"
        else:
            system_instruction = base_prompt + "\n\nCRITICAL FORMAT RULE:\n- Strictly use Markdown.\n- Use the section names exactly as listed, with empty lines between each section."
            mime_type = "text/plain"

        try:
            generation_config = {
                "system_instruction": system_instruction,
                "tools": [self.types.Tool(url_context=self.types.UrlContext())],
                "response_modalities": ["TEXT"],
                "response_mime_type": mime_type,
                **{key: policy[key] for key in (
                    "temperature", "top_p", "top_k", "max_output_tokens", "stop_sequences",
                ) if key in policy},
            }
            if thinking_level is not None:
                generation_config["thinking_config"] = {"thinking_level": thinking_level}
            # SDK camelCase aliases override snake_case defaults too. Replace
            # thinking_config as a whole to avoid combining a level and budget.
            for key in tuple(generation_config):
                first, *rest = key.split("_")
                alias = first + "".join(word.capitalize() for word in rest)
                if alias != key and alias in kwargs:
                    generation_config.pop(key)
            generation_config.update(kwargs)
            generation_config = self.types.GenerateContentConfig(**generation_config)
        except Exception as e:
            result["error"] = f"Invalid Gemini generation options: {e}"
            return result

        try:
            # The SDK expects milliseconds; configuration stores seconds.
            client = self.genai.Client(
                api_key=self.api_key, 
                http_options=self.types.HttpOptions(
                    base_url=policy.get("endpoints", {}).get("base_url"),
                    api_version=policy.get("api_version", "v1beta"),
                    timeout=timeout * 1000,
                    retry_options=self.types.HttpRetryOptions(
                        attempts=policy["retries"] + 1,
                        http_status_codes=[408, 429, 500, 502, 503, 504],
                    ),
                )
            )
        except Exception as e:
            result["error"] = f"Failed to initialize thread Client: {e}"
            return result

        try:
            response = self._generate_with_deadline(
                client, timeout,
                model=model_id,
                contents=user_content, 
                config=generation_config,
            )

            cand = response.candidates[0] if response.candidates else None
            
            # Parse URL Context Metadata
            if cand and cand.url_context_metadata and cand.url_context_metadata.url_metadata:
                meta = cand.url_context_metadata.url_metadata[0]
                
                if hasattr(meta, 'retrieved_url') and meta.retrieved_url:
                    result["retrieved_url"] = meta.retrieved_url
                    
                if meta.url_retrieval_status == self.types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS:
                    result["status"] = "Success"
                else:
                    result["status"] = "Failure"
                    status_name = meta.url_retrieval_status.name if hasattr(meta.url_retrieval_status, 'name') else str(meta.url_retrieval_status)
                    result["error"] = f"Bot Blocked / Page Unreadable ({status_name})"
                    return result 

            # Process Standard Text Response
            if not response.candidates:
                result["error"] = "API returned zero candidates."
            elif not cand.content or not cand.content.parts:
                reason = cand.finish_reason
                result["error"] = f"Blocked/Empty. Finish Reason: {reason}"
                if cand.finish_message:
                    result["error"] += f". {cand.finish_message}"
                result["status"] = "Failure"
            else:
                full_text = "\n".join(
                    part.text for part in cand.content.parts
                    if part.text and not getattr(part, "thought", False)
                )
                
                if output_format.lower() == "json":
                    import json
                    try:
                        cleaned_text = full_text.strip()
                        if cleaned_text.startswith("```json"):
                            cleaned_text = cleaned_text[7:]
                        elif cleaned_text.startswith("```"):
                            cleaned_text = cleaned_text[3:]
                        if cleaned_text.endswith("```"):
                            cleaned_text = cleaned_text[:-3]
                            
                        result["extracted_content"] = json.loads(cleaned_text.strip())
                    except Exception as e:
                        result["error"] = f"Failed to parse JSON string: {e}"
                        result["extracted_content"] = full_text 
                else:
                    result["extracted_content"] = full_text

        except (asyncio.TimeoutError, TimeoutError, _httpx.TimeoutException):
            result["status"] = "Failure"
            result["error"] = f"Timeout: URL retrieval exceeded {timeout:g} seconds."
        except self.errors.ClientError as e:
            result["status"] = "Failure"
            error_str = str(e)
            if "DEADLINE_EXCEEDED" in error_str or "504" in error_str:
                result["error"] = "Timeout: The page or API took too long to respond."
            elif "502" in error_str or "Bad Gateway" in error_str:
                result["error"] = "Bad Gateway: Google's server encountered a temporary error trying to reach the site."
            else:
                result["error"] = f"API ClientError: {error_str}"
        except Exception as e:
            result["status"] = "Failure"
            error_str = str(e)
            if "DEADLINE_EXCEEDED" in error_str or "504" in error_str:
                result["error"] = "Timeout: The page or API took too long to respond."
            elif "502" in error_str or "Bad Gateway" in error_str:
                result["error"] = "Bad Gateway: Google's server encountered a temporary error trying to reach the site."
            else:
                result["error"] = f"Unexpected Error: {error_str}"
        finally:
            try:
                client.close()
            except Exception as e:
                result["status"] = "Failure"
                result["error"] = result["error"] or f"Failed to close retrieval client: {e}"

        return result
