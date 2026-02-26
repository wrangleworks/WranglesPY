import os
import pandas as pd
import wrangles
import textwrap

from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("SERPAPI_API_KEY")
google_api_key = os.getenv("GEMINI_API_KEY")

df_in = pd.DataFrame([
    {
        "ID": 1,
        "suppliers": ["SKF"],
        "MPN": "P2B 207-SRB-SRE",
        "part_codes": ["P2B 207-SRB-SRE"],
        "Description": "pillow blcok bearing",
        "Site": "skf.com",
        "queries": ["SKF P2B 207-SRB-SRE pillow blcok bearing site:skf.com"]
    },
    {
        "ID": 2,
        "suppliers": ["Regal Rexnord"],
        "MPN": "10086528",
        "part_codes": ["10086528"],
        "Description": "",
        "Site": "",
        "queries": ["Regal Rexnord 10086528"]
    },
    {
        "ID": 3,
        "suppliers": ["BRADY"],
        "MPN": "M21125C342",
        "part_codes": ["M21125C342"],
        "Description": "LABEL CARTRIDGE",
        "Site": "",
        "queries": ["BRADY M21125C342","BRADY WORLDWIDE M21125C342 235IN X 7FT LABEL CARTRIDGE"]
    }
])

recipe = f"""
wrangles:
  - search.find_links:
      input: queries
      output: results
      api_key: {api_key}
      n_results: 3
      country: us
      location: Austin, Texas
      
  - compute.score_search_results:
      input:
        - results          
        - suppliers       
        - part_codes
        - MPN
        - Description      
      output: 
        - scored_results
        - Score Summary
      blacklist_keywords: 
        - ebay
      must_match_part_code: false
      mpn_exact_score: 8.0
      part_code_exact_score: 6.0
      
  - explode:
      input:
        - scored_results
        - Score Summary
        
  - split.dictionary:
      input: scored_results
      
  - select.element:
      input: summary['part_code_found']
      output: part_code_found
      
  - filter:
      input: part_code_found
      equal: true
      
  - search.retrieve_link_content:
      input: summary
      output: 
        - retrieved_data
        - Retrieved Content
      output_format: json
      api_key: {google_api_key}
      threads: 10
      
write:
  - file:
      name: search_results_output.xlsx
      columns:
        - ID
        - summary
        - scoring_details
        - Score Summary
        - pricing
        - metadata
        - part_code_found
        - retrieved_data
        - Retrieved Content
"""

df_out = wrangles.recipe.run(recipe, dataframe=df_in)
