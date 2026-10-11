# Search-result part-code evidence

`compute.score_search_results` scores classic search payloads and adds two
diagnostic fields to each scored-result dictionary:

- `part_code_matches`: reduced evidence from the result's title, snippet, and URL.
- `part_code_match_count`: the number of distinct candidate/type/source matches
  collected before redundancy removal.

These fields are nested alongside `summary`, `pricing`, `scoring_details`, and
`metadata`. They do not add a third recipe output. A single output column still
receives scored dictionaries; two output columns still receive dictionaries and
formatted summaries. The numeric scores, filtering, and result ordering are
unchanged.

## Evidence records

The keys in each record appear in this order:

| Key | Values or meaning |
| --- | --- |
| `match_type` | `MPN` for an MPN input, or `Codes` for a `part_codes` input. |
| `match_level` | `exact`, `stripped`, or `partial`. |
| `match_source` | `title`, `snippet`, or `url`. |
| `matched_code` | The matching text from the result, preserving its case and separators. |
| `input_code` | The input candidate, with surrounding whitespace removed. |

Matching is case-insensitive. `exact` means the complete source code matches the
input apart from case. `stripped` means the codes match after normalization with
the existing alphanumeric helper, which removes punctuation and spaces and folds
international characters. `partial` means the normalized input is contained in
a larger source code. Partial matching requires at least four normalized input
characters to avoid incidental matches for short codes.

For example, `NATV6-PP-A` against `natv6-pp-a` is exact, `LBBR14-2LS` against
`LBBR 14-2LS` is stripped, and `NATV6` against `NATV6-X-PP-A` is partial. A
standalone `085-196-225` followed by sentence punctuation remains exact.

The diagnostic levels describe the source evidence more precisely than the
existing scoring labels. In particular, the existing scoring evaluator can
award its exact-match score to normalized embedded text; this does not turn a
diagnostic partial match into an exact one.

## Redundancy removal and counts

Each result contains zero or one MPN record, placed before all Code records even
when the MPN match is partial. The strongest MPN evidence wins: exact before
stripped before partial, then the longer normalized input, then title before
snippet before URL.

Code records are removed when they repeat an MPN input that matched, their
normalized input is contained in the selected MPN input, or their normalized
matched text is contained in the selected MPN matched text. Remaining records
with the same normalized matched code are collapsed across sources, using the
same strength, input-length, and source preferences.

`part_code_match_count` is recorded before these reductions. It includes the MPN
repeated in `part_codes` and evidence from multiple sources, but does not count
identical duplicate candidates or repeated occurrences within one source. It is
an evidence count, not a count of distinct products or codes. No matches produces
an empty list and a count of zero.

For an MPN of `NATV6-PP-A`, `part_codes` of `[NATV6-PP-A, NATV6]`, and a title of
`INA NATV6-PP-A track roller` with no other matching fields, the result includes:

```json
{
  "part_code_matches": [
    {
      "match_type": "MPN",
      "match_level": "exact",
      "match_source": "title",
      "matched_code": "NATV6-PP-A",
      "input_code": "NATV6-PP-A"
    }
  ],
  "part_code_match_count": 3
}
```
