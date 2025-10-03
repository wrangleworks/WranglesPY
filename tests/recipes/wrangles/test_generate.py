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
                examples:
                    - input: "Thermostat with 24 V control"
                      output:  
                          category: hvac
                          primary_value: 24.0
                          unit: V  
                      notes: "primary values should be floats if possible"

                    - input: "4K 55 inch smart TV"
                      output:  
                          category: television
                          primary_value: 55
                          unit: inch   
                      notes: "primary values should be integers if possible and the unit is inch"
                    
                 """   ,
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
                examples:
                    - input: "Thermostat with 24 V control"
                      output:  
                          category: hvac
                          primary_value: 24.0
                          unit: V  
                      notes: "primary values should be floats if possible"

                    - input: "4K 55 inch smart TV"
                      output:  
                          category: television
                          primary_value: 55
                          unit: inch   
                      notes: "primary values should be integers if possible and the unit is inch"
        """,
        dataframe=data
    )

    assert df.at[0, "short_description"]  # non-empty
    assert df.at[0, "category"] or df.at[0, "short_description"]
    assert df.at[0, "source"] == "input"
    
