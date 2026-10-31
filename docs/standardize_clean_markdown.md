# Markdown escape cleanup in standardize.clean

`unescape_markdown` is an independent, opt-in option for the Python API and recipe
wrangle. It defaults to `False`; omitting it preserves existing behavior.

```python
import wrangles

wrangles.standardize.clean(r"\(OP50\)", unescape_markdown=True)  # "(OP50)"
wrangles.standardize.clean(r"PART123\_", unescape_markdown=True)  # "PART123_"
wrangles.standardize.clean(r"08B\-2", unescape_markdown=True)    # "08B-2"
```

```yaml
- standardize.clean:
    input: ai_mode_results
    output: ai_mode_results_clean
    unescape_unicode: true
    latex_to_text: true
    unescape_markdown: true
    collapse_whitespace: false
    trim: false
```

For example, `Manufacturing \> Machine Tools` becomes
`Manufacturing > Machine Tools`. Only the escape backslash is removed; the
punctuation remains. HTML decoding and deduplication are separate operations.

## Preservation and cleanup order

The Markdown toggle recognizes escaped ASCII punctuation in prose. It preserves
Markdown link destinations, reference definitions, autolinks, HTTP(S) URLs,
inline code, fenced code (including an unclosed fence), and indented code. Link
labels can be cleaned while their destinations remain unchanged.

Windows drive paths, UNC paths, and recognizable relative backslash paths are
protected. Quote paths containing spaces when mixing them with prose to protect
one whole path span. Both single and double quotes protect drive, UNC, and
explicit relative paths. Unquoted path spans stop at whitespace so adjacent prose can
still be cleaned. An unprefixed token containing a valid Unicode escape anywhere, such as
`A\_B\u0026C`, is treated as escaped prose, not a path. Use an explicit drive, UNC, or `.\` prefix to disambiguate
actual paths with Unicode-looking directory names. Doubled backslashes are
literal data and remain doubled; letter
escapes such as literal `\n`, unknown commands, and trailing backslashes remain
unchanged. Escaped numeric currency, ordinary prices, and unsupported formulas
remain intact, including multiline TeX spans with indented formula bodies.
Inline LaTeX can touch preceding prose or punctuation. Ambiguous TeX-delimited expressions with commands or math syntax
are preserved; parenthesized prose such as `\(OP50\)` is unescaped.

1. Identify existing code, destinations, URLs, and display math with the shared
   Markdown scanner.
2. Scan remaining prose once. Recognize inline LaTeX before Markdown punctuation
   escapes; convert only the existing supported units, symbols, and fractions
   when `latex_to_text` is enabled. Preserve unsupported math. Decode printable
   Unicode tokens only when `unescape_unicode` is enabled, and remove recognized
   Markdown escapes only when `unescape_markdown` is enabled.
3. Apply the existing encoding/HTML/Unicode normalization and control-character
   cleanup, then whitespace normalization and trimming.

Replacement text is not rescanned. For example, with both unescaping options
on, literal `\u005c_` becomes `\_`, rather than being decoded twice to `_`.
The preservation rules above describe this token cleanup; the other `clean`
options still operate as configured. Use `collapse_whitespace: false` and
`trim: false` to retain Markdown layout, and `unescape_html: false` if HTML
entities must remain literal. Mixed-value lists retain their shape and order;
non-string cells are unchanged.

## AI Mode runtime rollout

The toggle has no dependency on AI Mode headings, product semantics, description
links, or Google viewer handling. Release the updated package and make it
available in the recipe runtime before changing deployed recipes to use it.
Then replace only the duplicate Markdown-unescaping logic in the recipe-local
response function with `unescape_markdown: true`. Retain the separate description
link and Google-viewer handling, and preserve the raw provider response.

The deployed recipe-local workaround is not removed by this library change.
