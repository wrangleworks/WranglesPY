import requests as _requests
import yaml as _yaml
import json as _json
import copy as _copy

def chatGPT(
  data: any,
  api_key: str,
  settings: dict,
  timeout: int = 15
):
    """
    Submit a request to openAI chatGPT.

    :param data: Dict with the data for that row
    :param api_key: OpenAI API Key
    """
    if len(data) == 1:
        content = list(data.values())[0]
    else:
        content = _yaml.dump(data, indent=2)

    settings_local = _copy.deepcopy(settings)
    settings_local["messages"].append(
        {
            "role": "user",
            "content": f"\n---Data:\n---\n{content}"
        }
    )

    try:
        response = _requests.post(
            url = "https://api.openai.com/v1/chat/completions",
            headers = {
                "Authorization": f"Bearer {api_key}"
            },
            json = settings_local,
            timeout=timeout
        )
    except _requests.exceptions.ReadTimeout:
        if settings_local.get("functions", []):
            return {
                param: "Timed Out"
                for param in 
                settings_local.get("functions", [])[0]["parameters"]["required"]
            }
        else:
            return "Timed Out"
    except Exception as e:
        if settings_local.get("functions", []):
            return {
                param: e
                for param in 
                settings_local.get("functions", [])[0]["parameters"]["required"]
            }
        else:
            return e

    if response.ok:
        try:
            function_call = response.json()['choices'][0]['message']['function_call']
            return _json.loads(function_call['arguments'])
        except:
            try:
                return response.json()['choices']
            except:
                return response.text
    else:
        try:
            return response.json()['error']['message']
        except:
            return 'Failed'
