"""Structured answers to common questions about text or records.

``choose``, ``score``, and ``true_false`` answer one question type at a time;
``answers`` supports any combination of these types.
Each input record is evaluated in one request. Python results are dictionaries
of named answers; recipe wrappers project their fields into columns.
"""

import copy as _copy
import json as _json
import math as _math
import os as _os
import re as _re
from urllib.parse import urlsplit as _urlsplit

from . import ai_cache as _cache
from . import ai_config as _config
from .clients import typesafe as _typesafe


_KINDS = {"choose": "choice", "score": "score", "true_false": "noul"}
_FIELDS = {
    "choose": ("choice", "confidence", "probabilities"),
    "score": ("score", "confidence", "probabilities"),
    "true_false": ("probability_true", "true_criteria"),
}
_IDENTIFIER = _re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*\Z")
_PLACEHOLDER = _re.compile(r"\{\{\s*(.*?)\s*\}\}", _re.DOTALL)


def _json_value(value, location):
    """Validate JSON without quoting private input values in an exception."""
    def check(item):
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float and _math.isfinite(item):
            return
        if isinstance(item, list):
            for child in item:
                check(child)
            return
        if isinstance(item, dict) and all(isinstance(key, str) for key in item):
            for child in item.values():
                check(child)
            return
        raise ValueError

    try:
        check(value)
        # Also rejects circular containers before copying or sending requests.
        _json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise ValueError(f"{location} must contain finite JSON-compatible values and string object keys.") from None


def _description(value, location, *, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, (str, dict, list)):
        raise ValueError(f"{location} must be text, an object, or an array.")
    if not value or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{location} must not be empty.")
    _json_value(value, location)


def _prepare_questions(questions, kind=None):
    """Validate question definitions and resolve their positional output names."""
    if kind is not None and kind not in _KINDS:
        raise ValueError("Unknown AI question type.")
    if not isinstance(questions, dict) or not questions:
        raise ValueError("questions must be a non-empty mapping of labels to definitions.")
    prepared = {}
    destinations = set()
    for label, definition in questions.items():
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Question labels must be non-empty strings.")
        if not isinstance(definition, dict):
            raise ValueError("Each question must be an object.")
        if set(definition) - {"type", "instructions", "criteria", "output", "for_each"}:
            raise ValueError("Question definitions only accept type, instructions, criteria, output, and for_each.")
        expansion = definition.get("for_each")
        if "for_each" in definition:
            if not isinstance(expansion, dict) or set(expansion) != {"values", "variable"}:
                raise ValueError("for_each must define values and variable.")
            if not isinstance(expansion["values"], str) or not expansion["values"].strip():
                raise ValueError("for_each values must name a source column or record field.")
            variable = expansion["variable"]
            if not isinstance(variable, str) or not _IDENTIFIER.fullmatch(variable):
                raise ValueError("for_each variable must be an ASCII identifier containing letters, digits, or underscores.")
        question_kind = definition.get("type", kind)
        if not isinstance(question_kind, str) or question_kind not in _KINDS:
            raise ValueError("Question type must be choose, score, or true_false.")
        if kind is not None and question_kind != kind:
            raise ValueError(f"ai.{kind} only accepts {kind} questions.")
        instructions = definition.get("instructions")
        _description(instructions, "Question instructions")
        criteria = definition.get("criteria")
        if question_kind == "choose":
            if not isinstance(criteria, dict) or not 1 <= len(criteria) <= 255:
                raise ValueError("Choose criteria must map between 1 and 255 option labels to descriptions.")
            for option, description in criteria.items():
                if not isinstance(option, str) or not option.strip():
                    raise ValueError("Choose option labels must be non-empty strings.")
                _description(description, "Choose criterion", nullable=True)
        elif question_kind == "score":
            if (not isinstance(criteria, list) or not 2 <= len(criteria) <= 10
                    or any(not isinstance(item, str) or not item.strip() for item in criteria)):
                raise ValueError("Score criteria must be an ordered list of 2 to 10 non-empty string descriptions.")
            if len(set(criteria)) != len(criteria):
                raise ValueError("Score criterion descriptions must be unique probability labels.")
        elif "criteria" in definition:
            if not isinstance(criteria, dict) or set(criteria) - {"true", "false"}:
                raise ValueError('True/false criteria must be an object with quoted "true"/"false" keys.')
            for description in criteria.values():
                _description(description, "True/false criterion")

        fields = _FIELDS[question_kind]
        names = definition.get("output")
        if expansion is not None:
            if names is None or (isinstance(names, str) and not names.strip()):
                names = [label]
            elif isinstance(names, str):
                names = [names]
            elif (not isinstance(names, list) or len(names) != 1
                    or not isinstance(names[0], str) or not names[0].strip()):
                raise ValueError("for_each output must be blank, a column name, or a list containing one column name.")
        elif names is None or (isinstance(names, str) and not names.strip()):
            names = [label, *(f"{label}_{field}" for field in fields[1:])]
        elif (not isinstance(names, list) or len(names) != len(fields)
                or any(not isinstance(name, str) or not name.strip() for name in names)):
            raise ValueError(f"{question_kind} output must be blank or a list of {len(fields)} non-empty column names.")
        if len(set(names)) != len(names) or destinations.intersection(names):
            raise ValueError("AI output column names must be unique across all questions.")
        destinations.update(names)
        normalized = {"type": question_kind, "instructions": _copy.deepcopy(instructions),
                      "output": list(names)}
        if "criteria" in definition:
            normalized["criteria"] = _copy.deepcopy(criteria)
        if expansion is not None:
            normalized["for_each"] = dict(expansion)
        prepared[label] = normalized
    return prepared


def _output_columns(questions, kind=None):
    """Collect destinations before execution, including recipes selecting no rows."""
    return [name for question in _prepare_questions(questions, kind).values()
            for name in question["output"]]


def _wire_questions(prepared):
    return {
        label: {"type": _KINDS[question["type"]], "instructions": question["instructions"],
                **({"criteria": question["criteria"]} if "criteria" in question else {})}
        for label, question in prepared.items()
    }


def _render_template(value, aliases, local):
    """Substitute string values once; object keys and inserted data stay literal."""
    if isinstance(value, str):
        def substitute(match):
            name = match.group(1).strip()
            if not _IDENTIFIER.fullmatch(name):
                raise ValueError("AI template references must be ASCII identifiers; use underscores for spaces or punctuation.")
            if name in local:
                replacement = local[name]
            else:
                matches = aliases.get(name, [])
                if not matches:
                    raise ValueError(f"AI template reference {name!r} does not match a source column or local variable.")
                if len(matches) > 1:
                    raise ValueError(f"AI template reference {name!r} is ambiguous because source columns share the same normalized name.")
                replacement = matches[0]
            _json_value(replacement, "AI template value")
            return replacement if isinstance(replacement, str) else _json.dumps(
                replacement, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        return _PLACEHOLDER.sub(substitute, value)
    if isinstance(value, list):
        return [_render_template(item, aliases, local) for item in value]
    if isinstance(value, dict):
        return {key: _render_template(item, aliases, local) for key, item in value.items()}
    return value


def _row_plan(state, context, prepared):
    """Prepare one effective request and keep its result projection separate."""
    aliases = {}
    for name, value in context.items():
        if isinstance(name, str):
            alias = _re.sub(r"[^a-zA-Z0-9_]", "_", name)
            aliases.setdefault(alias, []).append(value)

    expanded = {}
    groups = {}
    reserved_labels = set(prepared)
    next_label = 0

    def render(question, local):
        result = {
            "type": question["type"],
            "instructions": _render_template(question["instructions"], aliases, local),
        }
        if "criteria" in question:
            result["criteria"] = _render_template(question["criteria"], aliases, local)
        return result

    for label, question in prepared.items():
        expansion = question.get("for_each")
        if expansion is None:
            expanded[label] = render(question, {})
            groups[label] = None
            continue

        field = expansion["values"]
        if field not in context:
            raise ValueError(f"for_each values names a missing source column or record field: {field!r}.")
        candidates = context[field]
        if not isinstance(candidates, (list, dict)):
            raise ValueError("for_each source values must be a list or a dictionary with string keys.")
        _json_value(candidates, "for_each source values")
        keyed = isinstance(candidates, dict)
        items = candidates.items() if keyed else ((None, value) for value in candidates)
        group = {"keyed": keyed, "items": []}
        for key, value in items:
            # Blank strings reserve a result slot without asking a question.
            if isinstance(value, str) and not value.strip():
                group["items"].append((None, key, value))
                continue
            while True:
                wire_label = f"_wrangles_question_{next_label}"
                next_label += 1
                if wire_label not in reserved_labels:
                    break
            reserved_labels.add(wire_label)
            expanded[wire_label] = render(question, {expansion["variable"]: value})
            group["items"].append((wire_label, key, _copy.deepcopy(value)))
        groups[label] = group

    # Rendering can make otherwise valid criteria empty or duplicate. Validate
    # the complete row before resolving credentials or making any request.
    # Destinations were checked on the original definitions. Validate each
    # rendered question independently so generated labels never introduce
    # irrelevant collisions between default (unused) projection columns.
    rendered = {label: _prepare_questions({label: definition})[label]
                for label, definition in expanded.items()}
    return {"state": state, "prepared": rendered, "wire": _wire_questions(rendered), "groups": groups}


def _project_answers(response, plan):
    answers = _answers(response, plan["prepared"])
    result = {}
    for label, group in plan["groups"].items():
        if group is None:
            result[label] = answers[label]
            continue
        result[label] = {} if group["keyed"] else []
        for wire_label, key, value in group["items"]:
            answer = {} if wire_label is None else {
                "value": _copy.deepcopy(value), **answers[wire_label]}
            if group["keyed"]:
                result[label][key] = answer
            else:
                result[label].append(answer)
    return result


def _answers(response, prepared):
    result = {}
    for label, question in prepared.items():
        answer = response["answers"][label]
        kind = question["type"]
        if kind == "true_false":
            result[label] = {
                "probability_true": answer["noul"],
                "true_criteria": _copy.deepcopy(question.get("criteria", {}).get("true", "")),
            }
        else:
            value_field = _FIELDS[kind][0]
            probabilities = answer["probabilities"]
            if kind == "score":
                probabilities = {description: probabilities[str(index)]
                                 for index, description in enumerate(question["criteria"])}
            else:
                probabilities = {option: probabilities[option] for option in question["criteria"]}
            result[label] = {value_field: answer[value_field], "confidence": answer["confidence"],
                             "probabilities": probabilities}
    return result


def _positive_number(value, name):
    try:
        valid = type(value) in (int, float) and _math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be a positive finite number.")
    return value


def _run(data, questions, kind, *, api_key, model, provider, protocol, threads,
         timeout, retries, cache, cache_ttl, contexts=None):
    prepared = _prepare_questions(questions, kind)
    rows = data if isinstance(data, list) else [data]
    for row in rows:
        if not isinstance(row, (str, dict, list)):
            raise ValueError("Each AI input must be text, a JSON object, or an array.")
        _json_value(row, "AI input")
    if contexts is None:
        contexts = [row if isinstance(row, dict) else {} for row in rows]
    elif (not isinstance(contexts, list) or len(contexts) != len(rows)
          or any(not isinstance(context, dict) for context in contexts)):
        raise ValueError("AI template contexts must be a list of records matching the input rows.")
    plans = [_row_plan(row, context, prepared) for row, context in zip(rows, contexts)]
    # All input/question validation precedes credentials and any provider request.
    if not rows:
        return []
    pending = [plan for plan in plans if plan["wire"]]
    if not pending:
        results = [_project_answers({"answers": {}}, plan) for plan in plans]
        return results if isinstance(data, list) else results[0]

    operation = f"ai.{kind or 'answers'}"
    settings = _config.resolve(operation, model=model, provider=provider, protocol=protocol)
    if settings["provider"] != "typesafe" or settings["protocol"] != "systemone":
        raise ValueError("AI answer wrangles currently require provider typesafe and protocol systemone.")
    workers = threads if threads is not None else settings.get("default_concurrency")
    if type(workers) is not int or workers < 1:
        raise ValueError("threads/default_concurrency must be a positive integer.")
    request_timeout = _positive_number(
        timeout if timeout is not None else settings.get("request_timeout_seconds"), "timeout")
    attempts = retries if retries is not None else settings.get("retries")
    if type(attempts) is not int or attempts < 0:
        raise ValueError("retries must be a non-negative integer.")
    url = settings.get("endpoints", {}).get("systemone")
    try:
        parsed_url = _urlsplit(url) if isinstance(url, str) else None
        valid_url = (parsed_url is not None and parsed_url.scheme == "https" and parsed_url.hostname
                     and not parsed_url.username and not parsed_url.password and not parsed_url.fragment)
    except ValueError:
        valid_url = False
    if not valid_url:
        raise ValueError("The Typesafe systemone endpoint must be an HTTPS URL without embedded credentials or fragments.")

    secret = api_key if api_key is not None else _os.getenv("TYPESAFE_API_KEY")
    if not isinstance(secret, str) or not secret.strip():
        raise ValueError("Set api_key or TYPESAFE_API_KEY for AI answer wrangles.")
    secret = secret.strip()
    if any(ord(char) < 33 or ord(char) > 126 for char in secret):
        raise ValueError("The Typesafe API key must contain only printable ASCII without whitespace.")
    if cache_ttl is not None:
        _positive_number(cache_ttl, "cache_ttl")
    policy = _cache.resolve_policy(settings.get("cache", {}), enabled=cache, ttl_seconds=cache_ttl,
                                  env_prefix="WRANGLES_AI_CACHE")
    _positive_number(policy.ttl_seconds, "cache_ttl")
    _config.warn_if_deprecated(settings["model"], provider=settings["provider"])
    def key_for(plan):
        static_request = {"endpoint": url, "model": settings["model"], "questions": plan["wire"]}
        return _cache.make_key(namespace=operation, provider=settings["provider"],
                               protocol=settings["protocol"], tenant_secret=secret,
                               static_request=static_request, data=plan["state"])

    def compute(plan):
        return _typesafe.call_systemone(state=plan["state"], questions=plan["wire"], model=settings["model"],
                                       api_key=secret, url=url, timeout=request_timeout, retries=attempts)

    responses = _cache.execute_batch(pending, key_for=key_for, compute=compute, cacheable=lambda result: True,
                                    max_workers=workers, policy=policy, preflight_first=True)
    responses = iter(responses)
    results = [_project_answers(next(responses) if plan["wire"] else {"answers": {}}, plan)
               for plan in plans]
    return results if isinstance(data, list) else results[0]


def choose(data, questions, api_key=None, *, model=None, provider=None, protocol=None,
           threads=None, timeout=None, retries=None, cache=None, cache_ttl=None):
    """Answer which option best fits; return choice, confidence, and probabilities.

    ``data`` is text/a record, or a list of input records. Each question supplies
    instructions and a mapping of option labels to descriptions (or None).
    A scalar input returns a named-answer dictionary; a list returns an ordered
    list of those dictionaries. Model and runtime defaults come from the catalog.

    Instruction and criterion string values accept ``{{ field_name }}``
    references to input-record fields (spaces/punctuation become underscores).
    ``for_each`` names a list/dictionary field in ``values`` and binds each
    candidate to ``variable``. List sources return lists of candidate answers;
    dictionary sources return dictionaries preserving the original keys.
    Blank string candidates retain their key or position as an empty dictionary
    without generating a provider question.
    Python calls using these features must supply the referenced fields in
    their input records.
    """
    return _run(data, questions, "choose", api_key=api_key, model=model, provider=provider,
                protocol=protocol, threads=threads, timeout=timeout, retries=retries,
                cache=cache, cache_ttl=cache_ttl)


def score(data, questions, api_key=None, *, model=None, provider=None, protocol=None,
          threads=None, timeout=None, retries=None, cache=None, cache_ttl=None):
    """Answer where the input falls along ordered, unique criterion descriptions.

    Scores retain the provider's native 0..N-1 scale. Confidence and complete
    probabilities keyed by description accompany each score. Input/output batch
    shape, input-record templates, ``for_each``, and configuration follow
    :func:`choose`.
    """
    return _run(data, questions, "score", api_key=api_key, model=model, provider=provider,
                protocol=protocol, threads=threads, timeout=timeout, retries=retries,
                cache=cache, cache_ttl=cache_ttl)


def true_false(data, questions, api_key=None, *, model=None, provider=None, protocol=None,
               threads=None, timeout=None, retries=None, cache=None, cache_ttl=None):
    """Answer how likely statements are to be true for the supplied input.

    Each named answer includes probability_true and the supplied true_criteria.
    Optional criteria use string keys "true" and "false". No Boolean conversion
    is performed. Input/output batch shape, input-record templates, ``for_each``,
    and configuration follow :func:`choose`.
    """
    return _run(data, questions, "true_false", api_key=api_key, model=model, provider=provider,
                protocol=protocol, threads=threads, timeout=timeout, retries=retries,
                cache=cache, cache_ttl=cache_ttl)


def answers(data, questions, api_key=None, *, model=None, provider=None, protocol=None,
            threads=None, timeout=None, retries=None, cache=None, cache_ttl=None):
    """Provide structured answers to common question types about each input.

    Each question declares type choose, score, or true_false with its instructions
    and criteria. Any combination of these types is answered in one request per
    input record. Instructions and criteria support input-record templates and
    ``for_each`` as described in :func:`choose`. Outputs follow the corresponding
    individual wrangles; repeated results retain their source collection shape.
    """
    return _run(data, questions, None, api_key=api_key, model=model, provider=provider,
                protocol=protocol, threads=threads, timeout=timeout, retries=retries,
                cache=cache, cache_ttl=cache_ttl)
