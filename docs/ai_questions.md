# AI questions

`ai.choose`, `ai.score`, `ai.true_false`, and `ai.questions` answer named questions
about each input record through Typesafe. They use the existing
[AI model catalog](ai_configuration.md), with `provider: typesafe`,
`protocol: systemone`, and the pinned model `jev-1.13.0` as defaults.

`extract.ai` keeps its current API and behavior. The new `ai` namespace leaves
room for a later compatible `ai.extract` migration; that alias is not introduced
here.

## Named questions and answers

Every operation takes a nonempty `questions` mapping. Its keys are the question
names and form the default output column names. Every question has
`instructions`, which can be a string, a JSON object, or a JSON array.
Instructions and supplied descriptions must be nonempty; choose descriptions
may also use `null` when the option label is sufficient.

| Operation | Criteria | Answer fields and default recipe columns |
| --- | --- | --- |
| `ai.choose` | A mapping of 1–255 nonblank option labels to descriptions. Descriptions can be strings, JSON objects, JSON arrays, or `null`. | `choice` → `<name>`; `confidence` → `<name>_confidence`; `probabilities` → `<name>_probabilities` |
| `ai.score` | An ordered list of 2–10 unique nonblank strings describing the scoring criteria. Structured criteria objects are not accepted. | `score` → `<name>`; `confidence` → `<name>_confidence`; `probabilities` → `<name>_probabilities` |
| `ai.true_false` | Optional `"true"` and/or `"false"` descriptions, supplied as strings, JSON objects, or JSON arrays. Quote these keys in YAML. | `probability_true` → `<name>`; `true_criteria` → `<name>_true_criteria` |
| `ai.questions` | Each question declares `type: choose`, `type: score`, or `type: true_false` and uses the corresponding schema above. | The columns for that question's type. |

The individual operations allow several questions of the same type. Their
`type` field may be omitted; if supplied, it must match the operation.
`ai.questions` requires each question's `type`, allowing all three types in one
request per input record.

Choose probabilities use the option labels as keys. Score probabilities use the
exact criterion strings as keys, preserving their order. The score is Typesafe's
native numeric score from `0` to `N-1`, where `N` is the number of criteria;
there is no `scale` parameter or automatic rescaling.
True/false returns a probability, without inventing a Boolean decision,
`probability_false`, or confidence score. Its `true_criteria` field preserves
the question's supplied `"true"` criterion, including structured JSON; if that
criterion is omitted, the value is an empty string.

## Recipes

The examples assume a `Description` input column and a managed secret named
`TYPESAFE_API_KEY`. Local recipes can also resolve this placeholder from that
environment variable. Never put the key value in a recipe or the model catalog.

Choose from named options:

```yaml
wrangles:
  - ai.choose:
      input: Description
      api_key: ${TYPESAFE_API_KEY}
      questions:
        Product Class:
          instructions: Choose the class supported by the product description.
          criteria:
            Bearing: A component supporting a rotating shaft.
            Belt: A flexible loop that transfers motion.
            Other: None of the named classes is supported.
```

This adds `Product Class`, `Product Class_confidence`, and
`Product Class_probabilities`.

Score against an ordered set of criteria:

```yaml
wrangles:
  - ai.score:
      input: Description
      api_key: ${TYPESAFE_API_KEY}
      questions:
        Description Quality:
          instructions: Assess how specifically this description identifies the product.
          criteria:
            - The product cannot be identified.
            - The general product type can be identified.
            - The product type and distinguishing specifications can be identified.
```

This adds `Description Quality`, `Description Quality_confidence`, and
`Description Quality_probabilities`. The probability mapping keeps those three
criterion sentences as its keys.

Evaluate a true/false question:

```yaml
wrangles:
  - ai.true_false:
      input: Description
      api_key: ${TYPESAFE_API_KEY}
      questions:
        Stainless Steel:
          instructions: Is the product explicitly described as stainless steel?
          criteria:
            "true": The description explicitly identifies stainless steel.
            "false": The description identifies a different material or omits the material.
```

This adds `Stainless Steel` containing `probability_true` and
`Stainless Steel_true_criteria`. A downstream rule can apply the threshold
appropriate for the workflow.

Combine question types in one operation:

```yaml
wrangles:
  - ai.questions:
      input: [Manufacturer, Part Number, Description]
      api_key: ${TYPESAFE_API_KEY}
      questions:
        Product Class:
          type: choose
          instructions: Select the product class using all available fields.
          criteria:
            Bearing: A component supporting a rotating shaft.
            Belt: A flexible loop that transfers motion.
            Other: None of the named classes is supported.
        Description Quality:
          type: score
          instructions: Assess how specifically the description identifies the product.
          criteria:
            - The product cannot be identified.
            - The general product type can be identified.
            - The product type and distinguishing specifications can be identified.
        Stainless Steel:
          type: true_false
          instructions: Is the product explicitly described as stainless steel?
          criteria:
            "true": The product information explicitly identifies stainless steel.
            "false": The product information identifies another material or omits material.
```

### Output names

Omitting a question's `output`, setting it to `null`, or using an empty or
whitespace-only string selects the default columns. To rename columns, supply
the complete ordered list inside that question:

```yaml
questions:
  Product Class:
    instructions: Choose the product class.
    criteria:
      Bearing: A component supporting a rotating shaft.
      Other: Any other product.
    output: [Class, Class Confidence, Class Probabilities]
```

Choose and score require exactly three output names; true/false requires exactly
two, in the order shown in the answer table. Every name must be a nonblank
string. Partial lists, an empty list, and a single nonempty string are invalid.
Output names must also be unique across all questions in the operation.
The operation's `questions` mapping controls the outputs; there is no single
operation-level `output` selection.

## Python

The public functions share these parameters:

```python
from wrangles import ai

ai.choose(data, questions, api_key=None, *, model=None, provider=None,
          protocol=None, threads=None, timeout=None, retries=None,
          cache=None, cache_ttl=None)
ai.score(data, questions, api_key=None, *, model=None, provider=None,
         protocol=None, threads=None, timeout=None, retries=None,
         cache=None, cache_ttl=None)
ai.true_false(data, questions, api_key=None, *, model=None, provider=None,
              protocol=None, threads=None, timeout=None, retries=None,
              cache=None, cache_ttl=None)
ai.questions(data, questions, api_key=None, *, model=None, provider=None,
             protocol=None, threads=None, timeout=None, retries=None,
             cache=None, cache_ttl=None)
```

A string or dictionary input returns a dictionary of named answers. A list of
strings or dictionaries returns one named-answer dictionary per input record,
in input order. Question definitions use the same schema as the recipe examples.

```python
from wrangles import ai

# The client uses TYPESAFE_API_KEY from the environment when api_key is omitted.
answers = ai.choose(
    {"Description": "Stainless steel ball bearing"},
    questions={
        "Product Class": {
            "instructions": "Choose the product class.",
            "criteria": {"Bearing": "Supports a rotating shaft.", "Other": None},
        },
    },
)
selected_class = answers["Product Class"]["choice"]
probabilities = answers["Product Class"]["probabilities"]
```

Python returns the answer fields listed in the table rather than flattened
column names. A question's `output` names are recipe column controls.

## Runtime settings and compatibility

Runtime options override the operation's catalog settings: `threads` controls
concurrent requests, `timeout` is in seconds, and `retries` counts additional
attempts after the initial request. The defaults are 10 threads, 30 seconds,
and one retry. Use `retries: 0` to disable retries. Only transient failures are
retried; invalid credentials, question definitions, and malformed results fail.
Errors do not become fabricated classification answers.

Successful results are cached in memory by request identity. The packaged
defaults enable a one-hour TTL, up to 512 entries, and up to 65,536 bytes per
cached value. Concurrent duplicate requests share one in-flight request.
Use `cache: false` or `cache_ttl` in seconds to override the corresponding
catalog values. Process-level environment controls take precedence:

- `WRANGLES_AI_CACHE_ENABLED`
- `WRANGLES_AI_CACHE_TTL_SECONDS`
- `WRANGLES_AI_CACHE_MAX_ENTRIES`
- `WRANGLES_AI_CACHE_MAX_VALUE_BYTES`
- `WRANGLES_AI_CACHE_SINGLE_FLIGHT`
- `WRANGLES_AI_CACHE_LOG_EVERY`

These controls do not change `extract.ai`'s existing
`WRANGLES_EXTRACT_AI_CACHE_*` settings. Provider, endpoint, model, credentials,
input, and question definitions are included in the cache identity, preventing
results from being shared across different requests or credentials. Secrets
and raw prompts are not written into cache keys or logs. Cache logging is
disabled by default for these operations.

A version-1 AI configuration uses packaged defaults for the new operations.
A version-2 replacement file must include their provider and operation entries;
missing entries are not silently merged. Only Typesafe's `systemone` adapter is
implemented for these functions, even if another provider appears in the catalog.
Explicit Typesafe model names may be supplied; the provider determines whether
that model is available.

See the [Typesafe introduction](https://docs.typesafe.ai/introduction) for the
provider's API documentation. Offline tests validate request and response
contracts; live accuracy, account limits, and deployment behavior require a
separate live-service check.
