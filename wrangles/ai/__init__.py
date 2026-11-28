"""Structured questions and dataframe Agents.

``choose``, ``score``, and ``true_false`` answer one question type at a time;
``decisions`` supports any combination of these types; ``answers`` remains a
compatible alias.
Each input record is evaluated in one request. Python results are dictionaries
of named answers; recipe wrappers project their fields into columns.
"""

from ._decisions import _FIELDS, _output_columns, _prepare_questions, _run, _validate_decimals
from ..api_config import INHERIT as _INHERIT

__all__ = ["choose", "score", "true_false", "decisions", "answers", "agent", "skill"]


def agent(df, input, output, instructions=None, skill=None, skill_package=None,
          model="gpt-5-mini", api_key=None, timeout=120, skills=None):
    """Run inline instructions and optional local Skills on selected dataframe columns."""
    from .agents.runtime import run
    return run(df, input, output, instructions=instructions, skill=skill, skill_package=skill_package,
               model=model, api_key=api_key, timeout=timeout, skills=skills)


def skill(df, input, output, skill=None, skill_package=None, model="gpt-5-mini", api_key=None,
          timeout=120, model_id=None):
    """Apply one named Skill through the dataframe Agent runtime."""
    if (skill is None) == (model_id is None):
        raise ValueError("Select one Skill using skill or model_id")
    return agent(df, input, output, skill=skill if model_id is None else model_id, skill_package=skill_package,
                 model=model, api_key=api_key, timeout=timeout)


def choose(data, questions, api_key=None, *, model=None, provider=None, protocol=None,
           threads=None, timeout=None, retries=None, cache=None, cache_ttl=None, decimals=2):
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

    ``decimals`` sets non-negative output precision for scores, confidence, and
    probabilities across all providers; the default is 2.
    """
    return _run(data, questions, "choose", api_key=api_key, model=model, provider=provider,
                protocol=protocol, threads=threads, timeout=timeout, retries=retries,
                cache=cache, cache_ttl=cache_ttl, decimals=decimals)


def score(data, questions, api_key=None, *, model=None, provider=None, protocol=None,
          threads=None, timeout=None, retries=None, cache=None, cache_ttl=None, decimals=2):
    """Answer where the input falls along ordered, unique criterion descriptions.

    Scores retain the provider's native 0..N-1 scale. Confidence and complete
    probabilities keyed by description accompany each score. Input/output batch
    shape, input-record templates, ``for_each``, and configuration follow
    :func:`choose`.
    """
    return _run(data, questions, "score", api_key=api_key, model=model, provider=provider,
                protocol=protocol, threads=threads, timeout=timeout, retries=retries,
                cache=cache, cache_ttl=cache_ttl, decimals=decimals)


def true_false(data, questions, api_key=None, *, model=None, provider=None, protocol=None,
               threads=None, timeout=None, retries=None, cache=None, cache_ttl=None, decimals=2):
    """Answer how likely statements are to be true for the supplied input.

    Each named answer includes probability_true and the supplied true_criteria.
    Optional criteria use string keys "true" and "false". No Boolean conversion
    is performed. Input/output batch shape, input-record templates, ``for_each``,
    and configuration follow :func:`choose`.
    """
    return _run(data, questions, "true_false", api_key=api_key, model=model, provider=provider,
                protocol=protocol, threads=threads, timeout=timeout, retries=retries,
                cache=cache, cache_ttl=cache_ttl, decimals=decimals)


def decisions(data, questions, api_key=None, *, model=None, provider=None, protocol=None,
              threads=None, timeout=None, retries=None, cache=None, cache_ttl=None, decimals=_INHERIT):
    """Provide structured answers to common question types about each input.

    Each question declares type choose, score, or true_false with its instructions
    and criteria. Any combination of these types is answered in one request per
    input record. Instructions and criteria support input-record templates and
    ``for_each`` as described in :func:`choose`. Outputs follow the corresponding
    individual wrangles; repeated results retain their source collection shape.
    Configuration and cache identity retain the ``ai.answers`` role for
    compatibility with existing catalogs and calls.
    """
    return _run(data, questions, None, api_key=api_key, model=model, provider=provider,
                protocol=protocol, threads=threads, timeout=timeout, retries=retries,
                cache=cache, cache_ttl=cache_ttl, decimals=decimals)


def answers(data, questions, api_key=None, *, model=None, provider=None, protocol=None,
            threads=None, timeout=None, retries=None, cache=None, cache_ttl=None, decimals=_INHERIT):
    """Compatibility alias for :func:`decisions`, with identical inputs and outputs."""
    return decisions(data, questions, api_key=api_key, model=model, provider=provider,
                     protocol=protocol, threads=threads, timeout=timeout, retries=retries,
                     cache=cache, cache_ttl=cache_ttl, decimals=decimals)
