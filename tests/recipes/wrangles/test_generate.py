import os 
import pandas as pd 
import pytest 
import wrangles
@pytest.mark.skipif("OPENAI_API_KEY" not in os.environ,
                    reason="needs live OpenAI access")
