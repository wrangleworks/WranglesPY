import os
from typing import Optional, Dict, Any
from unittest import result

def _get_genai():
    """Lazy loader for Google GenAI SDK to prevent hard dependencies."""
    try:
        from google import genai
        from google.genai import types, errors
        return genai, types, errors
    except ImportError:
        raise ImportError(
            "The google-genai package is required for URL context retrieval. "
            "Install it with: pip install google-genai"
        )

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

    def retrieve(self, url: str, prompt: Optional[str] = None, model_id: str = "models/gemini-3-flash-preview", output_format: str = "markdown") -> Dict[str, Any]:
        """
        Retrieves context from a web URL using the Gemini API.
        Includes thread-safe initialization, strict timeouts, and optional JSON parsing.
        """
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
            
        user_content = f"Please retrieve content from this explicitly bounded URL: <{url}>"

        try:
            # Thread-safe client initialization with a 45-second timeout
            client = self.genai.Client(
                api_key=self.api_key, 
                http_options=self.types.HttpOptions(
                    api_version="v1beta",
                    timeout=45000 # 45 seconds
                )
            )
        except Exception as e:
            result["error"] = f"Failed to initialize thread Client: {e}"
            return result

        base_prompt = prompt if prompt else self.DEFAULT_SYSTEM_PROMPT
        
        # Format-specific prompting
        if output_format.lower() == "json":
            system_instruction = base_prompt + "\n\nCRITICAL FORMAT RULE:\n- You must return the requested sections as a strictly valid JSON object where the section names are the keys."
            mime_type = "application/json"
        else:
            system_instruction = base_prompt + "\n\nCRITICAL FORMAT RULE:\n- Strictly use Markdown.\n- Use the section names exactly as listed, with empty lines between each section."
            mime_type = "text/plain"

        try:
            response = client.models.generate_content(
                model=model_id,
                contents=user_content, 
                config=self.types.GenerateContentConfig(
                    system_instruction=system_instruction, 
                    tools=[self.types.Tool(url_context=self.types.UrlContext())],
                    response_modalities=["TEXT"],
                    response_mime_type=mime_type,
                    temperature=0.1,
                )
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
            elif not response.candidates[0].content:
                reason = response.candidates[0].finish_reason
                result["error"] = f"Blocked/Empty. Finish Reason: {reason}"
                if result["status"] != "Success":
                    result["status"] = "Failure"
            else:
                full_text = "\n".join([part.text for part in response.candidates[0].content.parts])
                
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

        return result