"""Dataframe adapters for structured AI answers to common question types."""

import pandas as _pd
import yaml as _yaml

from .. import ai as _ai


_FIELDS = _ai._FIELDS


def _output_columns(questions, kind=None):
    """Resolve nested destinations before filtering or concurrent execution."""
    return _ai._output_columns(questions, kind=kind)


def _run(df, questions, kind, input=None, **settings):
    prepared = _ai._prepare_questions(questions, kind=kind)
    if df.empty:
        for question in prepared.values():
            for column in question["output"]:
                if column not in df.columns:
                    df[column] = _pd.Series(index=df.index, dtype=object)
        return df

    source = df if input is None else df[input if isinstance(input, list) else [input]]
    # Templates can reference the full row even when only selected columns are
    # sent as the provider's shared state. Unreferenced columns stay local.
    results = _ai._run(source.to_dict(orient="records"), questions, kind,
                       contexts=df.to_dict(orient="records"), **settings)
    if not isinstance(results, list) or len(results) != len(df):
        raise RuntimeError("AI response count does not match the input row count.")
    for label, question in prepared.items():
        if "for_each" in question:
            df[question["output"][0]] = [result[label] for result in results]
            continue
        for column, field in zip(question["output"], _FIELDS[question["type"]]):
            df[column] = [result[label][field] for result in results]
    return df


def choose(df: _pd.DataFrame, questions: dict, input=None, api_key=None,
           model=None, provider=None, protocol=None, threads=None, timeout=None,
           retries=None, cache=None, cache_ttl=None) -> _pd.DataFrame:
    return _run(df, questions, "choose", input=input, api_key=api_key,
                model=model, provider=provider, protocol=protocol, threads=threads,
                timeout=timeout, retries=retries, cache=cache, cache_ttl=cache_ttl)


def score(df: _pd.DataFrame, questions: dict, input=None, api_key=None,
          model=None, provider=None, protocol=None, threads=None, timeout=None,
          retries=None, cache=None, cache_ttl=None) -> _pd.DataFrame:
    return _run(df, questions, "score", input=input, api_key=api_key,
                model=model, provider=provider, protocol=protocol, threads=threads,
                timeout=timeout, retries=retries, cache=cache, cache_ttl=cache_ttl)


def true_false(df: _pd.DataFrame, questions: dict, input=None, api_key=None,
               model=None, provider=None, protocol=None, threads=None, timeout=None,
               retries=None, cache=None, cache_ttl=None) -> _pd.DataFrame:
    return _run(df, questions, "true_false", input=input, api_key=api_key,
                model=model, provider=provider, protocol=protocol, threads=threads,
                timeout=timeout, retries=retries, cache=cache, cache_ttl=cache_ttl)


def answers(df: _pd.DataFrame, questions: dict, input=None, api_key=None,
            model=None, provider=None, protocol=None, threads=None, timeout=None,
            retries=None, cache=None, cache_ttl=None) -> _pd.DataFrame:
    return _run(df, questions, None, input=input, api_key=api_key,
                model=model, provider=provider, protocol=protocol, threads=threads,
                timeout=timeout, retries=retries, cache=cache, cache_ttl=cache_ttl)


def _description_schema(nullable=False):
    variants = [
        {"type": "string", "pattern": r"\S"},
        {"type": "object", "minProperties": 1},
        {"type": "array", "minItems": 1},
    ]
    if nullable:
        variants.append({"type": "null"})
    return {"anyOf": variants}


def _question_schema(kind):
    fields = _FIELDS[kind]
    positional_output = {
        "oneOf": [
            {"type": "null"},
            {"type": "string", "pattern": r"^\s*$"},
            {"type": "array", "minItems": len(fields), "maxItems": len(fields),
             "uniqueItems": True, "items": {"type": "string", "pattern": r"\S"}},
        ],
    }
    grouped_output = {
        "oneOf": [
            {"type": "null"},
            {"type": "string"},
            {"type": "array", "minItems": 1, "maxItems": 1,
             "items": {"type": "string", "pattern": r"\S"}},
        ],
    }
    properties = {
        "type": {"type": "string", "enum": [kind],
                 "description": "Question type to answer; optional for a wrangle dedicated to one type."},
        "instructions": {**_description_schema(),
                         "description": (
                             "Question to answer about this row's input, as text or structured instructions. "
                             "String values support {{ column_name }} references to the current row, "
                             "with non-alphanumeric characters replaced by underscores. "
                             "Templates work with or without for_each; missing or ambiguous references fail."
                         )},
        "for_each": {
            "type": "object", "additionalProperties": False,
            "required": ["values", "variable"],
            "description": (
                "Construct one question per item in this row's source collection, except blank strings. "
                "All constructed and ordinary questions share one provider request per row. "
                "The output is one column matching the source collection: a list of answers for a list, "
                "or a dictionary of answers retaining the original keys for a dictionary. "
                "Empty or whitespace-only strings produce {} at the original key or list position, "
                "without generating a provider question. Missing keys or positions are not added. "
                "Other JSON values are not skipped. "
                "An empty list produces [], and an empty dictionary produces {}."
            ),
            "properties": {
                "values": {
                    "type": "string", "pattern": r"\S",
                    "description": (
                        "Exact source column name, never a literal collection. "
                        "Each cell must contain a list or a dictionary with string keys. "
                        "Use empty-string entries to reserve slots that return {} without scoring. "
                        "The source column can be outside the selected input columns."
                    ),
                },
                "variable": {
                    "type": "string", "pattern": r"^[A-Za-z_][A-Za-z0-9_]*$",
                    "description": (
                        "Local template variable for the current list item or dictionary value. "
                        "Use {{ variable_name }} in instructions or criterion descriptions. "
                        "This binding takes precedence over column shorthand within this question."
                    ),
                },
            },
        },
        "output": {
            "description": (
                "Destination columns in order: " + ", ".join(fields) + ". "
                "Omit, use null, or use a blank string for defaults. "
                "Defaults are the question label followed by _confidence and _probabilities "
                "for `ai.choose`/`ai.score`, or the question label and _true_criteria for `ai.true_false`. "
                "An explicit list must name every output column. "
                "With for_each, use one column name or a single-entry list; "
                "blank defaults to the question label. Each answer retains value and its answer fields; "
                "blank-string candidate placeholders return {}."
            ),
            "type": ["null", "string", "array"],
        },
    }
    required = ["instructions"]
    if kind == "score":
        properties["criteria"] = {
            "type": "array", "minItems": 2, "maxItems": 10,
            "uniqueItems": True, "items": {"type": "string", "pattern": r"\S"},
            "description": (
                "Distinct criterion descriptions used as probability keys. "
                "For `ai.score`, order defines the native zero-based score positions; no custom scale. "
                "Descriptions support {{ column_name }} and local for_each variable references. "
                "Rendered descriptions must remain distinct and become the probability keys."
            ),
        }
        required.append("criteria")
    elif kind == "choose":
        properties["criteria"] = {
            "type": "object", "minProperties": 1, "maxProperties": 255,
            "propertyNames": {"pattern": r"\S"},
            "additionalProperties": _description_schema(nullable=True),
            "description": (
                "Choice labels mapped to their descriptions or structured criteria. "
                "Description string values support row and for_each template references; labels stay literal."
            ),
        }
        required.append("criteria")
    else:
        properties["criteria"] = {
            "type": "object", "propertyNames": {"enum": ["true", "false"]},
            "additionalProperties": _description_schema(),
            "description": (
                "Optional criteria keyed by the strings true and false; quote these YAML keys. "
                "Description string values support row and for_each template references. "
                "The rendered true criterion is retained in the true_criteria output."
            ),
        }
    return {"type": "object", "additionalProperties": False,
            "required": required, "properties": properties,
            "allOf": [{"if": {"required": ["for_each"]},
                       "then": {"properties": {"output": grouped_output}},
                       "else": {"properties": {"output": positional_output}}}]}


def _schema(kind):
    descriptions = {
        "choose": (
            "Answers which option best fits the input, "
            "with the choice, confidence, and complete probabilities. "
        ),
        "score": (
            "Answers where the input falls along ordered criteria, "
            "with the native score, confidence, and complete probabilities. "
        ),
        "true_false": (
            "Answers how likely a statement is to be true for the input, "
            "with probability_true and the supplied true_criteria. "
        ),
        None: (
            "Answers any combination of `choose`, `score`, and `true_false` "
            "questions about the input with structured results. "
        ),
    }
    if kind is None:
        question_schemas = []
        for question_type in _FIELDS:
            question_schema = _question_schema(question_type)
            question_schema["required"].append("type")
            question_schemas.append(question_schema)
        question_definition = {"oneOf": question_schemas}
    else:
        question_definition = _question_schema(kind)
    return {
        "type": "object", "additionalProperties": False, "required": ["questions"],
        "description": (
            descriptions[kind]
            + "Accepts multiple named questions in one provider request per row. "
            "Question labels determine default output names."
        ),
        "properties": {
            "input": {"type": ["string", "integer", "array"],
                      "items": {"type": ["string", "integer"]},
                      "description": (
                          "Input column(s) sent as the shared provider state; omit to supply all columns. "
                          "Question templates and for_each sources can reference other columns in the row."
                      )},
            "questions": {"type": "object", "minProperties": 1,
                          "propertyNames": {"pattern": r"\S"},
                          "additionalProperties": question_definition,
                          "description": "Questions to answer for each input row, keyed by their distinct labels."},
            "api_key": {"type": "string", "description": "Typesafe API key; defaults to TYPESAFE_API_KEY."},
            "model": {"type": "string", "description": "Model ID; defaults to this wrangle's AI catalog selection."},
            "provider": {"type": "string", "enum": ["typesafe"],
                         "description": "Provider resolved through the AI catalog; currently typesafe."},
            "protocol": {"type": "string", "enum": ["systemone"],
                         "description": "Provider protocol selected through the AI catalog."},
            "threads": {"type": "integer", "minimum": 1,
                        "description": "Maximum row requests in parallel; defaults to the AI catalog."},
            "timeout": {"type": "number", "exclusiveMinimum": 0,
                        "description": "Per-attempt request timeout in seconds; defaults to the AI catalog."},
            "retries": {"type": "integer", "minimum": 0,
                        "description": "Additional attempts for retryable failures; defaults to the AI catalog."},
            "cache": {"type": "boolean", "description": "Reuse identical successful requests through the shared AI cache."},
            "cache_ttl": {"type": "number", "exclusiveMinimum": 0,
                          "description": "Override the cache result lifetime in seconds."},
        },
    }


for _name, _kind in (("choose", "choose"), ("score", "score"),
                     ("true_false", "true_false"), ("answers", None)):
    globals()[_name].__doc__ = _yaml.safe_dump(_schema(_kind), sort_keys=False)
