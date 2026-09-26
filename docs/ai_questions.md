# AI questions

`ai.choose`, `ai.score`, `ai.true_false`, and `ai.questions` answer named questions
about each input record through [Typesafe](https://docs.typesafe.ai/introduction).
They use the existing [AI model catalog](ai_configuration.md), with
`provider: typesafe`, `protocol: systemone`, and the pinned model `jev-1.13.0`
as defaults. `extract.ai` keeps its current API and behavior.

## Input and output schema

Every wrangle takes a nonempty `questions` mapping. Each key is a nonblank
question label, used to construct the default output column names. Each
question requires `instructions`: nonempty text, a JSON object, or a JSON array.
Objects must have string keys, and all supplied values must be JSON-compatible.

| Wrangle | Criteria | Answer fields and default output columns |
| --- | --- | --- |
| `ai.choose` | A mapping of 1–255 nonblank option labels to descriptions. Descriptions can be nonempty strings, JSON objects, JSON arrays, or `null`. | `choice` → `<label>`; `confidence` → `<label>_confidence`; `probabilities` → `<label>_probabilities` |
| `ai.score` | An ordered list of 2–10 unique nonblank strings describing the scoring levels. | `score` → `<label>`; `confidence` → `<label>_confidence`; `probabilities` → `<label>_probabilities` |
| `ai.true_false` | Optional `"true"` and/or `"false"` descriptions, supplied as nonempty strings, JSON objects, or JSON arrays. Quote these keys in YAML. | `probability_true` → `<label>`; `true_criteria` → `<label>_true_criteria` |
| `ai.questions` | Each question declares `type: choose`, `type: score`, or `type: true_false` and uses that type's criteria. | The columns for each question's type. |

`input` selects the columns to send for each row: one column name, a zero-based
column position, or a list of names/positions. Omit `input` to send all columns.
The selected values are sent together as a record keyed by column name, so a
question can use information from several columns. All questions in a wrangle
are evaluated together in one request per input row.

`ai.choose`, `ai.score`, and `ai.true_false` each accept multiple questions of
their own type. Their nested `type` field is optional; if supplied, it must
match the wrangle. `ai.questions` requires a `type` for every question.

Each example below includes an input table, a recipe to run against that table,
and an illustrative output. Outputs are shown as YAML records to make
dictionary-valued cells readable; the input columns remain in the result.
The numbers illustrate the output format and are not results from a live run.
Probabilities and confidence values use `0`–`1`, not percentages.

The examples use `api_key: ${TYPESAFE_API_KEY}`. Set that environment variable
locally or supply the managed secret as a recipe variable in a hosted recipe.

## `ai.choose`

`ai.choose` selects an option for each question and returns its confidence and
the full probability distribution. `ai.choose` probabilities use the option
labels as keys, including options with zero probability. See Typesafe's
[Choice documentation](https://docs.typesafe.ai/primitives/choice).

**Example input**

| Message |
| --- |
| The invoice lists two charges for one order. Please refund the extra charge. |

**Recipe**

```yaml
wrangles:
  - ai.choose:
      input: Message  # Column name; a list selects several columns. Omit for all.
      api_key: ${TYPESAFE_API_KEY}
      questions:  # Required mapping; add one entry per question.
        department:  # Question label; also the first default output column.
          # Required: nonempty text, object, or array.
          instructions: Which department should handle this message?
          # Required: 1–255 option labels mapped to descriptions.
          # Descriptions may be nonempty text, objects, arrays, or null.
          criteria:
            Billing: Charges, invoices, and refunds for payment errors.
            Delivery: Parcel tracking and delivery problems.
            Returns: Returning or exchanging a product.
          output:  # Blank uses department, department_confidence, department_probabilities.
        tone:  # A second question of the same type, sent in the same request.
          instructions: What is the customer's tone?
          criteria:
            Calm: null  # null is allowed when the label supplies enough meaning.
            Frustrated: null
            Angry: null
          # Optional: rename all three outputs, in this exact order.
          output: [Tone, Tone Confidence, Tone Probabilities]
```

**Example output**

```yaml
- Message: The invoice lists two charges for one order. Please refund the extra charge.
  department: Billing
  department_confidence: 1.0
  department_probabilities:
    Billing: 1.0
    Delivery: 0.0
    Returns: 0.0
  Tone: Calm
  Tone Confidence: 0.7
  Tone Probabilities:
    Calm: 0.8
    Frustrated: 0.2
    Angry: 0.0
```

## `ai.score`

`ai.score` rates the input against ordered descriptions. The order and number
of criteria define positions `0` through `N-1`. The returned score is the
probability-weighted position and may fall between levels; it is not itself a
probability. There is no `scale` parameter or automatic rescaling. See
Typesafe's [Score documentation](https://docs.typesafe.ai/primitives/score).

`ai.score` probabilities use the exact criterion descriptions as keys. This
wrangle accepts string descriptions for its levels, so each can serve as a
unique probability key.

**Example input**

| Message |
| --- |
| Export crashes in Safari but works in Chrome. Some users cannot switch browsers. |

**Recipe**

```yaml
wrangles:
  - ai.score:
      input: Message
      api_key: ${TYPESAFE_API_KEY}
      questions:
        bug_severity:
          instructions: How much does this issue prevent users from completing their work?
          # Required: 2–10 unique, nonblank strings, ordered from low to high.
          # These descriptions also become the probability keys.
          criteria:
            - Appearance issue; work is unaffected.              # Position 0
            - A feature fails; another method remains available. # Position 1
            - Work cannot continue using any available method.   # Position 2
          # output is omitted: bug_severity, bug_severity_confidence,
          # and bug_severity_probabilities are created automatically.
          # Add sibling questions here for additional scores on the same input.
```

**Example output**

```yaml
- Message: Export crashes in Safari but works in Chrome. Some users cannot switch browsers.
  bug_severity: 1.4
  bug_severity_confidence: 0.4
  bug_severity_probabilities:
    Appearance issue; work is unaffected.: 0.0
    A feature fails; another method remains available.: 0.6
    Work cannot continue using any available method.: 0.4
```

Here, `0 × 0.0 + 1 × 0.6 + 2 × 0.4 = 1.4`. The column named `bug_severity`
contains that native score; its companion columns retain confidence and the
complete probability distribution.

## `ai.true_false`

`ai.true_false` returns `probability_true` in the column named by the question
label. It also returns the supplied `"true"` criterion, or an empty string when
that criterion is omitted. It does not generate a Boolean, `probability_false`,
or a confidence column. See Typesafe's
[Noul documentation](https://docs.typesafe.ai/primitives/noul).

**Example input**

| Message |
| --- |
| I have asked three times now. Can I please speak to a real person? |

**Recipe**

```yaml
wrangles:
  - ai.true_false:
      input: Message
      api_key: ${TYPESAFE_API_KEY}
      questions:
        is_human_escalation:
          instructions: Is the customer asking to speak with a human agent?
          # criteria is optional. Without a "true" criterion, true_criteria is "".
        is_repeat_contact:
          instructions: Has the customer contacted support about this before?
          # Optional: either or both string keys "true" and "false".
          # Quote these YAML keys so they are not interpreted as Booleans.
          # Each description may be nonempty text, an object, or an array.
          criteria:
            "true": Mentions an earlier attempt to contact support.
            "false": Gives no indication of an earlier contact.
          # Optional output override: exactly [Probability Column, True Criteria Column].
          # Omitted here to construct both column names from is_repeat_contact.
```

**Example output**

```yaml
- Message: I have asked three times now. Can I please speak to a real person?
  is_human_escalation: 0.99
  is_human_escalation_true_criteria: ""
  is_repeat_contact: 0.94
  is_repeat_contact_true_criteria: Mentions an earlier attempt to contact support.
```

`is_repeat_contact: 0.94` is the probability that the statement is true.
The question label is the column name, not a separate value in the output.

## `ai.questions`

`ai.questions` combines `ai.choose`, `ai.score`, and `ai.true_false` question
types in one wrangle. Each question uses the same input record and retains its
type's output fields. See Typesafe's
[Primitives documentation](https://docs.typesafe.ai/primitives) for combining
question types.

**Example input**

| Message | Browser |
| --- | --- |
| Export crashes here but works in Chrome. I have reported this twice already. | Safari |

**Recipe**

```yaml
wrangles:
  - ai.questions:
      input: [Message, Browser]  # Both columns form one record for every question.
      api_key: ${TYPESAFE_API_KEY}
      questions:
        issue_type:
          type: choose  # Required here: choose, score, or true_false.
          instructions: Which kind of issue is being reported?
          criteria:  # The same option-to-description mapping used by ai.choose.
            Bug: A feature behaves incorrectly or fails.
            Account: Sign-in, access, or account administration.
            Other: A request outside those categories.
        bug_severity:
          type: score
          instructions: How much does this issue prevent users from completing their work?
          criteria:  # The same ordered list used by ai.score.
            - Appearance issue; work is unaffected.
            - A feature fails; another method remains available.
            - Work cannot continue using any available method.
        is_repeat_contact:
          type: true_false
          instructions: Has the customer contacted support about this before?
          criteria:  # The same optional descriptions used by ai.true_false.
            "true": Mentions an earlier attempt to contact support.
      # Each question can have its own output override; there is no outer output.
```

**Example output**

```yaml
- Message: Export crashes here but works in Chrome. I have reported this twice already.
  Browser: Safari
  issue_type: Bug
  issue_type_confidence: 1.0
  issue_type_probabilities:
    Bug: 1.0
    Account: 0.0
    Other: 0.0
  bug_severity: 1.4
  bug_severity_confidence: 0.4
  bug_severity_probabilities:
    Appearance issue; work is unaffected.: 0.0
    A feature fails; another method remains available.: 0.6
    Work cannot continue using any available method.: 0.4
  is_repeat_contact: 0.97
  is_repeat_contact_true_criteria: Mentions an earlier attempt to contact support.
```

## Output names

Omitting a question's `output`, setting it to `null`, or using an empty or
whitespace-only string selects the default columns. To rename them, supply the
complete ordered list inside that question, as shown for `tone` in the
`ai.choose` example.

`ai.choose` and `ai.score` require exactly three output names; `ai.true_false`
requires exactly two, in the order shown in the schema table. Every name must
be a nonblank string and unique across all questions in the wrangle. Partial
lists, an empty list, and a single nonempty string are invalid.

## Python

Like any other wrangle, these can also be called as Python functions:

```python
from wrangles import ai

# Uses TYPESAFE_API_KEY from the environment.
answers = ai.choose(
    "Stainless steel ball bearing",
    questions={
        "product_class": {
            "instructions": "Which product class fits this description?",
            "criteria": {"Bearing": "Supports a rotating shaft.", "Other": None},
        },
    },
)
print(answers["product_class"]["choice"])
```

A string or dictionary input returns named answers; a list returns one set of
named answers per input, in order. Question definitions match the YAML schema.

## Runtime settings and compatibility

Runtime options override the wrangle's catalog settings: `threads` controls
concurrent requests, `timeout` is the per-attempt timeout in seconds, and
`retries` counts additional attempts after the initial request. The defaults
are 10 threads, 30 seconds, and one retry. Use `retries: 0` to disable retries.
Only transient failures are retried; invalid credentials, question definitions,
and malformed results fail. Errors do not become fabricated answers.

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
disabled by default for these wrangles.

A version-1 AI configuration uses packaged defaults for the new wrangles.
A version-2 replacement file must include their provider and operation entries;
missing entries are not silently merged. Only Typesafe's `systemone` adapter is
implemented for these functions, even if another provider appears in the catalog.
Explicit Typesafe model names may be supplied; the provider determines whether
that model is available.
