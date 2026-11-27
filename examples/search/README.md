# Web-search recipe examples

Install WranglesPY with `python -m pip install -e .` from the repository root,
then set `SERPAPI_API_KEY` to your SerpAPI key.

[recipe_search_web.wrgl.yml](recipe_search_web.wrgl.yml) is a collection of
independent YAML documents, each illustrating a search. Copy one document
(between `---` separators) into its own recipe file and run:

```sh
wrangles.recipe search-example.wrgl.yml
```

Each example supplies its own input rows and writes JSON in the current
working directory. These examples call the live search provider.
