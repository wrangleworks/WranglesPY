import os 
import pandas as pd 
import pytest 
import wrangles
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
                - product_name
                - features
              output:
                short_description:
                  type: string
                  description: Short marketing copy.
                category:
                  type: string
                  description: Suggested category.
              api_key: ${OPENAI_API_KEY}
              model: gpt-5-nano
              web_search: false
              strict: true
        """,
        dataframe=data
    )


    assert df.at[0, "short_description"]  # non-empty
    assert df.at[0, "category"]
    assert df.at[0, "source"] == "internally generated"
