import os 
import pandas as pd 
import pytest 
import wrangles
import wrangles.generate

@pytest.mark.skipif("OPENAI_API_KEY" not in os.environ,
                    reason="needs live OpenAI access")
def test_generate_ai_recipe_without_web_search_real_call():
    data = pd.DataFrame({
        "product_name": ["Widget One"],
        "features": ["Lightweight; durable"]
    })

    df = wrangles.recipe.run(
        recipe="""
        wrangles:
            - generate.ai:
                input:
                    
                    - features
                output:
                    short_description:
                        type: string
                        description: Concise marketing blurb for the product.
                    category:
                        type: string
                        description: use any word of the input as category name.
                api_key: ${OPENAI_API_KEY}
                model: gpt-5-nano
                reasoning:
                    effort: low
                threads: 1
                web_search: false
                previous_response: false
                strict: true
                Example:
                    input:
                    - |
                        referred_example_index:1
                        PRODUCT DATA:
                        Name: Trailblazer Lantern
                        Features: Rechargeable; weather-proof; 3 brightness modes; Target category: Outdoor Lighting
                    - |
                        referred_example_index:1
                        PRODUCT DATA:
                        Name: Trailblazer Lantern
                        Features: Rechargeable; weather-proof; 3 brightness modes; Target category: Outdoor Lighting
                    output:
                    - |
                        {{
                        "short_description": "Trailblazer Lantern is a weather-proof rechargeable lantern with three brightness modes for campsite versatility."
                        }}
                    - |
                        {{
                        "category": "Outdoor Lighting"
                        }}
        """,
        dataframe=data
    )

    assert df.at[0, "short_description"]  # non-empty
    assert df.at[0, "category"]
    assert df.at[0, "source"] == "input"
    


def test_generate_ai_recipe_without_web_search_real_call_chain():
    data = pd.DataFrame({
        "product_name": ["Widget One"],
        "features": ["Lightweight; durable"]
    })

    df = wrangles.recipe.run(
        recipe="""
        wrangles:
            - generate.ai:
                input:
                    
                    - features
                output:
                    short_description:
                        type: string
                        description: Concise marketing blurb for the product.
                    category:
                        type: string
                        description: use any word of the input as category name.
                api_key: ${OPENAI_API_KEY}
                model: gpt-5-nano
                reasoning:
                    effort: low
                threads: 1
                web_search: false
                previous_response: True
                strict: true
                Example:
                    input:
                    - |
                        referred_example_index:1
                        PRODUCT DATA:
                        Name: Trailblazer Lantern
                        Features: Rechargeable; weather-proof; 3 brightness modes; Target category: Outdoor Lighting
                    - |
                        referred_example_index:1
                        PRODUCT DATA:
                        Name: Trailblazer Lantern
                        Features: Rechargeable; weather-proof; 3 brightness modes; Target category: Outdoor Lighting
                    output:
                    - |
                        {{
                        "short_description": "Trailblazer Lantern is a weather-proof rechargeable lantern with three brightness modes for campsite versatility."
                        }}
                    - |
                        {{
                        "category": "Outdoor Lighting"
                        }}
        """,
        dataframe=data
    )

    assert df.at[0, "short_description"]  # non-empty
    assert df.at[0, "category"] or df.at[0, "short_description"]
    assert df.at[0, "source"] == "input"
    
