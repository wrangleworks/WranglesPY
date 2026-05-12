# extract.ai — 2026 Refactor & Best Practices

## Overview

This document describes the changes made to `wrangles.extract.ai` and the supporting
`wrangles.openai` module as part of the 2026 best-practices update.
All changes are **fully backward-compatible** — existing recipe files and Python
scripts continue to work without modification.

---

## New Parameters

### `instructions`
**Type:** `str | list[str]`  **Default:** `None`

System-level guidance that applies to every row in the batch.
Use this instead of stuffing instructions into `output` descriptions.

```python
wrangles.extract.ai(
    data,
    api_key="...",
    output={"length": {"type": "string", "description": "Length found in text"}},
    instructions="Always return length values with their unit attached (e.g. '25mm', not '25').",
)
```

In a recipe:
```yaml
wrangles:
  - extract.ai:
      api_key: ${OPENAI_API_KEY}
      instructions: Always return length values with their unit attached.
      output:
        length:
          type: string
          description: Length found in text
```

Multiple instructions can be supplied as a list — each becomes a separate system message:

```python
instructions=[
    "Return all numeric values as integers.",
    "If no value is found, return an empty string.",
]
```

---

### `examples`
**Type:** `list[dict]`  **Default:** `None`

Few-shot examples that show the model the expected input → output mapping
**before** it processes real data. Each item must have an `"input"` key and
an `"output"` key whose value matches the shape of your `output` schema.

The examples are inserted as proper OpenAI tool-call message triples
(`user` / `assistant[tool_calls]` / `tool`) so the model treats them as
demonstrated completions, not just text descriptions.

```python
wrangles.extract.ai(
    data,
    api_key="...",
    output={"length": {"type": "string", "description": "Length"}},
    examples=[
        {"input": "bolt 10mm",  "output": {"length": "10mm"}},
        {"input": "cable 2m",   "output": {"length": "2m"}},
        {"input": "pipe 1.5ft", "output": {"length": "1.5ft"}},
    ],
)
```

In a recipe:
```yaml
wrangles:
  - extract.ai:
      api_key: ${OPENAI_API_KEY}
      examples:
        - input: bolt 10mm
          output:
            length: 10mm
        - input: cable 2m
          output:
            length: 2m
      output:
        length:
          type: string
          description: Length found in text
```

---

### `taxonomy`
**Type:** `dict | list`  **Default:** `None`

A controlled vocabulary the model is instructed to draw values from.
Accepts a flat list of valid values or a nested dict for hierarchical taxonomies.

```python
# Flat list
wrangles.extract.ai(
    data,
    api_key="...",
    output={"sentiment": {"type": "string", "description": "Sentiment"}},
    taxonomy=["positive", "negative", "neutral"],
)

# Hierarchical dict
wrangles.extract.ai(
    data,
    api_key="...",
    output={"category": {"type": "string", "description": "Product category"}},
    taxonomy={
        "Electronics": ["Phones", "Laptops", "Tablets"],
        "Clothing":    ["Shirts", "Trousers", "Shoes"],
    },
)
```

In a recipe:
```yaml
wrangles:
  - extract.ai:
      api_key: ${OPENAI_API_KEY}
      taxonomy:
        - positive
        - negative
        - neutral
      output:
        sentiment:
          type: string
          description: Sentiment of the text
```

---

### `max_completion_tokens`
**Type:** `int`  **Default:** `None`

Maximum tokens the model may generate per row. This is the current OpenAI
parameter name — the old `max_tokens` is deprecated and will be evicted
automatically if both are supplied.

```python
wrangles.extract.ai(
    data,
    api_key="...",
    output={"summary": {"type": "string", "description": "One-sentence summary"}},
    max_completion_tokens=100,
)
```

In a recipe:
```yaml
wrangles:
  - extract.ai:
      api_key: ${OPENAI_API_KEY}
      max_completion_tokens: 100
      output:
        summary:
          type: string
          description: One-sentence summary
```

---

## Internal Improvements

### Reasoning-model guard

OpenAI o-series models (`o1`, `o1-mini`, `o3`, `o3-mini`, `o4-mini`, …) reject
parameters like `temperature`, `top_p`, `presence_penalty`, and `frequency_penalty`
with a hard API error.

The guard detects any o-series model by name or by the pattern `^o\d` and silently
strips the incompatible parameters before the request is sent.

```python
# This now works without raising an error — temperature is stripped automatically
wrangles.extract.ai(
    data,
    api_key="...",
    model="o3-mini",
    temperature=0.2,          # stripped silently
    output={"length": {"type": "string", "description": "Length"}},
)
```

Detection lives in `wrangles.openai._is_reasoning_model()` so it can be reused
by other functions in the future.

---

### Rate-limit-aware backoff

Previously, retries used a fixed exponential backoff sequence (1 s, 2 s, 4 s, …)
regardless of what OpenAI said.

OpenAI 429 responses include a `Retry-After` header with the exact number of
seconds to wait. The retry loop now reads this header and sleeps that precise
duration. For non-429 errors the exponential sequence is unchanged.

```
Before:  429 received → sleep 1s → sleep 2s → sleep 4s   (guessing)
After:   429 received → sleep Retry-After value           (exact)
```

---

### Prompt construction centralised in `openai.build_extract_messages()`

All message assembly — base system prompts, instructions, taxonomy, few-shot
examples, and legacy messages — now lives in a single helper:

```
wrangles/openai.py :: build_extract_messages(
    instructions, examples, taxonomy, messages
) -> list[dict]
```

This makes it easy to reuse the same prompt logic in other contexts
(e.g. `generate.ai`, custom wrangles) and keeps `extract.ai()` free of
string-formatting code.

---

## Files Changed

| File | Change |
|---|---|
| `wrangles/openai.py` | Added `_REASONING_MODELS`, `_REASONING_UNSUPPORTED_PARAMS`, `_is_reasoning_model()`, `build_extract_messages()`; updated `chatGPT()` retry loop |
| `wrangles/extract.py` | Added `instructions`, `examples`, `taxonomy`, `max_completion_tokens`; reasoning-model guard; uses `build_extract_messages()` |
| `wrangles/recipe_wrangles/extract.py` | New params in signature, YAML schema, and forwarded to `_extract.ai()` |
| `tests/recipes/wrangles/test_extract.py` | `TestExtractAIPromptConstruction` (9), `TestExtractAIReasoningModelGuard` (5), `TestExtractAIMaxCompletionTokens` (3), `TestRateLimitAwareBackoff` (3) — all mocked |

---

## Backward Compatibility

Every new parameter defaults to `None` / not set.  
Existing recipe files and Python scripts require **zero changes**.

The only internal removal is the inline message-building block in `extract.ai()`,
which has been replaced by `build_extract_messages()` with identical output.
