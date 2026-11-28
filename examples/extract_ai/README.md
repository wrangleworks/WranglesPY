# Extraction recipe examples

Install WranglesPY from the repository root with `python -m pip install -e .`.
Set `OPENAI_API_KEY` in the environment before running these examples; they
make live API calls and can incur provider charges.

- Open [the recipe notebook](extract_ai_recipe_examples.ipynb) in Jupyter and
  select the Python environment where WranglesPY is installed. Its inputs are
  inline, so it does not depend on the notebook working directory.
- [The classification judge recipe](extract%20ai%20judge%20example.wrgl.yml)
  evaluates supplied candidate classifications. Set `INPUT_FILE` to the absolute
  path of a tab-separated file containing `Input Description` and one or more
  columns ending in ` Classification`. Each classification cell contains a
  dictionary with `L1`, `L2` and `L3` keys. From this directory, run:

  ```sh
  wrangles.recipe "extract ai judge example.wrgl.yml"
  ```

  The recipe writes `ai_classification_judge_results.json`,
  `ai_classification_judge_summary.json` and `ai_classification_judge.json`
  into the current directory.

See the [extraction guide](../../docs/extract_ai_user_guide.md) for usage details.
