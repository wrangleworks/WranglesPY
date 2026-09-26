"""Dataframe adapters for named AI questions."""

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
    operation = getattr(_ai, kind or "questions")
    results = operation(source.to_dict(orient="records"), questions=questions, **settings)
    if not isinstance(results, list) or len(results) != len(df):
        raise RuntimeError("AI response count does not match the input row count.")
    for label, question in prepared.items():
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


def questions(df: _pd.DataFrame, questions: dict, input=None, api_key=None,
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
    properties = {
        "type": {"type": "string", "enum": [kind],
                 "description": "Question type; optional for a wrangle with one question type."},
        "instructions": {**_description_schema(),
                         "description": "Question or structured instructions applied to this row's input."},
        "output": {
            "description": (
                "Destination columns in order: " + ", ".join(fields) + ". "
                "Omit, use null, or use a blank string for defaults. "
                "Defaults are the question label followed by _confidence and _probabilities "
                "for choose/score, or the question label and _true_criteria for true_false. "
                "An explicit list must name every output column."
            ),
            "oneOf": [
                {"type": "null"},
                {"type": "string", "pattern": r"^\s*$"},
                {"type": "array", "minItems": len(fields), "maxItems": len(fields),
                 "uniqueItems": True, "items": {"type": "string", "pattern": r"\S"}},
            ],
        },
    }
    required = ["instructions"]
    if kind == "score":
        properties["criteria"] = {
            "type": "array", "minItems": 2, "maxItems": 10,
            "uniqueItems": True, "items": {"type": "string", "pattern": r"\S"},
            "description": (
                "Distinct criterion descriptions used as probability keys. "
                "For score, order defines the native zero-based score positions; no custom scale."
            ),
        }
        required.append("criteria")
    elif kind == "choose":
        properties["criteria"] = {
            "type": "object", "minProperties": 1, "maxProperties": 255,
            "propertyNames": {"pattern": r"\S"},
            "additionalProperties": _description_schema(nullable=True),
            "description": "Choice labels mapped to their descriptions or structured criteria.",
        }
        required.append("criteria")
    else:
        properties["criteria"] = {
            "type": "object", "propertyNames": {"enum": ["true", "false"]},
            "additionalProperties": _description_schema(),
            "description": (
                "Optional criteria keyed by the strings true and false; quote these YAML keys. "
                "The true criterion is retained in the true_criteria output."
            ),
        }
    return {"type": "object", "additionalProperties": False,
            "required": required, "properties": properties}


def _schema(kind):
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
            "Ask named " + (kind.replace("_", "/") if kind else "mixed")
            + " questions in one provider request per row. "
            "Question labels determine default output names. Scores are native numeric scores; "
            "true_false returns the probability of true, without thresholding or a Boolean."
        ),
        "properties": {
            "input": {"type": ["string", "integer", "array"],
                      "items": {"type": ["string", "integer"]},
                      "description": "Input column(s); omit to supply all columns as a row record."},
            "questions": {"type": "object", "minProperties": 1,
                          "propertyNames": {"pattern": r"\S"},
                          "additionalProperties": question_definition,
                          "description": "Questions keyed by their distinct labels."},
            "api_key": {"type": "string", "description": "Typesafe API key; defaults to TYPESAFE_API_KEY."},
            "model": {"type": "string", "description": "Model ID; defaults to this operation's AI catalog selection."},
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
                     ("true_false", "true_false"), ("questions", None)):
    globals()[_name].__doc__ = _yaml.safe_dump(_schema(_kind), sort_keys=False)
