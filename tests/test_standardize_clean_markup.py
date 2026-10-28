"""Synthetic examples of escaped prose, units and protected Markdown content."""

import pandas as pd
import pytest
import yaml

import wrangles


@pytest.fixture(autouse=True)
def offline_recipe_context(monkeypatch):
    monkeypatch.setattr("wrangles.auth.get_applied_permission_group", lambda: None)

    def unexpected_network(*args, **kwargs):
        pytest.fail("Text cleanup tests must not make network requests")

    monkeypatch.setattr("socket.socket.connect", unexpected_network)


def _clean(value, **options):
    return wrangles.standardize.clean(
        value,
        collapse_whitespace=False,
        trim=False,
        uncurl_quotes=False,
        unescape_html=False,
        **options,
    )


@pytest.mark.parametrize(("original", "expected"), [
    (r"$12\text{ VDC}$", "12 VDC"),
    (r"$5.0\text{ A}$", "5.0 A"),
    (r"$80\text{ VAC}$ to $264\text{ VAC}$", "80 VAC to 264 VAC"),
    (r"$0\text{ }^\circ\text{C}$ to $\+60\text{ }^\circ\text{C}$", "0 °C to +60 °C"),
    (r"$20^{\circ}\mathrm{C}$", "20°C"),
    (r"$<0.15\text{ W}$", "<0.15 W"),
    (r"$\le 90\text{ }\mu\text{A}$", "≤ 90 µA"),
    (r"$2.5 \times 5.5 \times 11.0\text{ mm}$", "2.5 × 5.5 × 11.0 mm"),
    (r"$\$22.75$, $\$30.00$", "$22.75, $30.00"),
    (r"$\pm 5\%$ at $10\,\Omega$", "± 5% at 10 Ω"),
    (r"$\geq 5\text{ A}$, $\leq 20\text{ A}$", "≥ 5 A, ≤ 20 A"),
    (r"Price $19.99; output $12\text{ VDC}$.", "Price $19.99; output 12 VDC."),
])
def test_latex_units_and_symbols(original, expected):
    assert _clean(original, latex_to_text=True) == expected


@pytest.mark.parametrize(("original", "expected"), [
    ("$1/2$-inch", "1/2-inch"),
    ("$ 3 / 8 $", "3 / 8"),
    ("$-1/2$", "-1/2"),
    ("$1 1/2$ inch", "1 1/2 inch"),
    ("$1/2$ and $3/4$", "1/2 and 3/4"),
    ("Cost $18.57; pitch $1/2$ inch.", "Cost $18.57; pitch 1/2 inch."),
    ("[Size $1/2$](https://example.invalid/$3/8$)", "[Size 1/2](https://example.invalid/$3/8$)"),
])
def test_latex_numeric_fractions_without_commands(original, expected):
    assert _clean(original) == original
    assert _clean(original, latex_to_text=True) == expected


@pytest.mark.parametrize(("original", "expected"), [
    (r"$\$6\text{ mm}$", "6 mm"),
    (r"$\$19\text{ mm}$", "19 mm"),
    (r"$\$12\text{ mm}$", "12 mm"),
    (r"$\$5400\text{ N}$", "5400 N"),
    (r"$\$8000\text{ N}$", "8000 N"),
    (r"$\$5.4\mathrm{ kN}$", "5.4 kN"),
    (r"$\$12\text{ VDC}$", "12 VDC"),
    (r"$\$6\text{mm}$", "6mm"),
    (r"$\$6m$", "6m"),
    (r"$\$2\text{ furlongs/fortnight}$", "2 furlongs/fortnight"),
    (r"$\$1.5\text{ custom units}$", "1.5 custom units"),
    (r"$\$6\text{ mm} \times \$12\text{ mm}$", "6 mm × 12 mm"),
    (r"$\$-20^{\circ}\text{C}$", "-20°C"),
    (r"$\$0.15\text{ W}\pm 5\%$", "0.15 W± 5%"),
])
def test_latex_dollars_are_removed_without_recognizing_units(original, expected):
    assert _clean(original) == original
    assert _clean(original, latex_to_text=True) == expected
    assert _clean(expected, latex_to_text=True) == expected


@pytest.mark.parametrize(("original", "expected"), [
    (r"$\$80.98$", "$80.98"),
    (r"$\$20.60\text{ USD}$", "$20.60 USD"),
    (r"$\$6\text{ per mm}$", "$6 per mm"),
    (r"$\$6\text{/mm}$", "$6/mm"),
    (r"$\$6\text{ each}$", "$6 each"),
    (r"$\$6\text{ million}$", "$6 million"),
    (r"$\$6$", "$6"),
    (r"$\$0.50$", "$0.50"),
    (r"$\$.50$", "$.50"),
    (r"$\$1,234.50$", "$1,234.50"),
    (r"$\$1,234,567.89\text{ USD}$", "$1,234,567.89 USD"),
    (r"$\$-6.50$", "$-6.50"),
    (r"$\$6.00-\$12.00$", "$6.00-$12.00"),
    (r"$\$6.00\text{ USD}-\$12.00\text{ USD}$", "$6.00 USD-$12.00 USD"),
    (r"$\$6.00\text{ to }\$12.00\text{ USD per pack}$", "$6.00 to $12.00 USD per pack"),
    ("$6 mm", "$6 mm"),
    ("$6m", "$6m"),
    ("$1/2 off and $3 on sale", "$1/2 off and $3 on sale"),
    ("$1/2", "$1/2"),
    (r"\$1/2$", r"\$1/2$"),
    (r"$\$6\unknown{ mm}$", r"$\$6\unknown{ mm}$"),
])
def test_latex_cleanup_preserves_numeric_currency_and_protected_values(original, expected):
    assert _clean(original, latex_to_text=True) == expected


def test_literal_unicode_escapes_preserve_existing_unicode_and_backslashes():
    original = r"healthcare \u0026 ITE; \u00b0C; \U0001F50C; \uD83D\uDE00; \n \t \text" + " — Café ±"
    expected = r"healthcare & ITE; °C; 🔌; 😀; \n \t \text" + " — Café ±"
    assert _clean(original, unescape_unicode=True) == expected
    assert _clean(expected, unescape_unicode=True) == expected


@pytest.mark.parametrize("original", [
    r"\u0000 \u0009 \u000A \u007f",  # Control characters are not introduced.
    r"\uD800 \uDE00 \U00110000",  # Invalid or unsupported code points.
    r"\u12X4 \u123 \\u0026",  # Malformed or explicitly escaped literals.
])
def test_unsupported_unicode_escapes_are_preserved(original):
    assert _clean(original, unescape_unicode=True) == original


@pytest.mark.parametrize("original", [
    r"$\frac{1}{2}\text{ mm}$",
    r"$x^2 + y_1 \times 2$",
    r"$\unknown{12}$",
    r"$$12\text{ VDC}$$",
    r"Prices $22.75 and $30.00; discount 5%.",
    r"wall\-mount AC\-DC \(ITE\) and \*literal\*",
])
def test_unknown_math_currency_and_markdown_escapes_are_preserved(original):
    assert _clean(original, unescape_unicode=True, latex_to_text=True) == original


@pytest.mark.parametrize("protected", [
    r"`$1/2$`",
    r"$$1/2$$",
    r"https://example.invalid/?value=$1/2$",
    r"`$\$2\text{ custom units}$`",
    r"[source](https://example.com/?value=$\$2\text{custom-units}$)",
    r"$$\$2\text{ custom units}$$",
    r"`$12\text{ VDC}$ \u0026`",
    r"``a ` $12\text{ VDC}$ \u0026``",
    "```python\n" + r"$12\text{ VDC}$ \u0026" + "\n```",
    "~~~~\n```\n" + r"$12\text{ VDC}$ \u0026" + "\n~~~~~",
    "> ```\n> " + r"$12\text{ VDC}$ \u0026" + "\n> ```",
    "    " + r"$12\text{ VDC}$ \u0026",
    r"[source](https://example.com/item(a)?x=\u0026&y=$12\text{V}$)",
    r'''[source](<https://example.com/a(b)> "title ) \u0026 $12\text{V}$")''',
    r"[ref]: https://example.com/?x=\u0026",
    r"<https://example.com/?x=\u0026>",
    r"https://example.com/?x=\u0026",
    "$$\n" + r"12\text{ VDC} \u0026" + "\n$$",
])
def test_conversions_preserve_code_urls_and_display_math(protected):
    source = protected + "\n\n" + r"$12\text{ VDC}$; healthcare \u0026 ITE"
    expected = protected + "\n\n12 VDC; healthcare & ITE"
    assert _clean(source, unescape_unicode=True, latex_to_text=True) == expected


def test_unclosed_fence_is_not_rewritten():
    original = "```\n" + r"$12\text{ VDC}$ \u0026"
    assert _clean(original, unescape_unicode=True, latex_to_text=True) == original


def test_conversions_are_independently_opt_in():
    original = r"$12\text{ VDC}$; healthcare \u0026 ITE"
    assert _clean(original) == original
    assert _clean(original, unescape_unicode=True) == r"$12\text{ VDC}$; healthcare & ITE"
    assert _clean(original, latex_to_text=True) == r"12 VDC; healthcare \u0026 ITE"


def test_mixed_list_shapes_and_long_markdown_are_preserved():
    original = "# Heading\n\n" + "x" * 40000 + "\n\n" + r"$12\text{ VDC}$ \u0026"
    expected = original.rsplit("\n\n", 1)[0] + "\n\n12 VDC &"
    values = [original, "", None, 42, ["nested"]]
    assert _clean(values, unescape_unicode=True, latex_to_text=True) == [
        expected, "", None, 42, ["nested"]
    ]


def test_recipe_schema_and_dataframe_accessor_support_options():
    import jsonschema

    options = {
        "input": "raw",
        "output": "clean",
        "unescape_unicode": True,
        "latex_to_text": True,
        "collapse_whitespace": False,
        "trim": False,
    }
    schema = yaml.safe_load(wrangles.recipe._recipe_wrangles.standardize.clean.__doc__)
    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.validate(options, schema)
    source = r"$12\text{ VDC}$; healthcare \u0026 ITE"
    frame = wrangles.DataFrame({"raw": [source, 42]})
    recipe_result = wrangles.recipe.run(
        {"wrangles": [{"standardize.clean": options}]}, dataframe=frame.copy()
    )
    accessor_result = frame.wrangles.standardize.clean(**options)
    assert recipe_result["raw"].tolist() == [source, 42]
    assert recipe_result["clean"].tolist() == ["12 VDC; healthcare & ITE", 42]
    assert accessor_result.equals(recipe_result)


def test_cleanup_preserves_viewer_links_for_subsequent_semantic_extraction():
    label = "PartGo to product viewer dialog for this item."
    url = r"https://www.google.com/search?prds=item(1)&q=product&raw=\u0026"
    raw = f"[{label}]({url})"
    code = f"`{raw}`\n\n```\n{raw}\n```"
    text = "Go to product viewer dialog for this item."
    original = raw + "\n\n" + code + "\n\n" + text
    assert _clean(original, unescape_unicode=True, latex_to_text=True) == original


@pytest.mark.parametrize(("source", "expected"), [
    (r"\(OP50\)", "(OP50)"),
    (r"PART123\_", "PART123_"),
    (r"Manufacturing \> Machine Tools", "Manufacturing > Machine Tools"),
    (r"08B\-2", "08B-2"),
    (r"\!\#\%\&\*\+\,\-\.\/\:\;\<\=\>\?\@\[\]\^\_\`\{\|\}\~", "!#%&*+,-./:;<=>?@[]^_`{|}~"),
    ("\\\"quoted\\\"", '"quoted"'),
    (r"\$label", "$label"),
    ("", ""),
])
def test_markdown_unescaping_is_independently_opt_in(source, expected):
    assert _clean(source) == source
    assert _clean(source, unescape_markdown=False) == source
    assert _clean(source, unescape_markdown=True) == expected


@pytest.mark.parametrize("protected", [
    r"`A\_B`", r"``A ` B\_C``",
    "```python\n" + r"A\_B" + "\n```",
    "~~~\n" + r"A\_B" + "\n~~~",
    "> ```\n> " + r"A\_B" + "\n> ```",
    "    " + r"A\_B", "\t" + r"A\_B",
    r"[label](https://example.com/a\_b\(c\))",
    r'''[label](<https://example.com/a\_b> "title ) A\_B")''',
    r"[ref]: https://example.com/a\_b",
    r"<https://example.com/a\_b>", r"https://example.com/a\_b",
    r"C:\_cache\part\-2.txt", r"C:\Users\u0026\_data.txt",
    r"\\server\share\_part\-2", r".\_cache\file.txt", r"..\_cache\file.txt",
    r'"C:\Program Files\_cache\file.txt"',
    r"\_cache\file.txt", r"folder\part\_file.txt", r"C:\Program Files\_cache\file.txt",
    r"A\\_B", r"A\\\_B", r"A\\\\_B",
    r"A\nB \unknown trailing" + "\\",
    r"Prices $22.75 and $30.00", r"Price \$22.75; range \$20-\$30",
    r"$x^2 + y_1 \times 2$", r"$\unknown{A\_B}$",
    r"$$A\_B$$", r"\(x \times y\)", r"\[x^2 + y_1\]", r"\(x+1\)",
])
@pytest.mark.parametrize("other_options", [False, True])
def test_markdown_cleanup_preserves_protected_content(protected, other_options):
    source = protected + "\n\n" + r"PART123\_"
    assert _clean(
        source, unescape_markdown=True,
        unescape_unicode=other_options, latex_to_text=other_options,
    ) == protected + "\n\nPART123_"


@pytest.mark.parametrize(("options", "expected"), [
    ({"unescape_markdown": True}, r"$12\text{ VDC}$; healthcare \u0026; (OP50)"),
    ({"unescape_markdown": True, "unescape_unicode": True}, r"$12\text{ VDC}$; healthcare &; (OP50)"),
    ({"unescape_markdown": True, "latex_to_text": True}, r"12 VDC; healthcare \u0026; (OP50)"),
    ({"unescape_markdown": True, "unescape_unicode": True, "latex_to_text": True}, "12 VDC; healthcare &; (OP50)"),
])
def test_markdown_composes_with_unicode_and_latex(options, expected):
    source = r"$12\text{ VDC}$; healthcare \u0026; \(OP50\)"
    assert _clean(source, **options) == expected


def test_markdown_preserves_escaped_unicode_punctuation_and_list_shape():
    values = [r"\u005c_ \u0026 PART\_", "", None, 42, [r"A\_B"]]
    assert _clean(values, unescape_markdown=True, unescape_unicode=True) == [
        r"\_ & PART_", "", None, 42, [r"A\_B"],
    ]


def test_markdown_shared_helper_and_recipe_schema_forwarding():
    import jsonschema
    from wrangles._text_cleanup import clean_escaped_text

    assert clean_escaped_text(r"PART\_", unescape_markdown=True) == "PART_"
    options = {
        "input": "raw", "output": "clean", "unescape_markdown": True,
        "unescape_unicode": True, "latex_to_text": True,
        "collapse_whitespace": False, "trim": False,
    }
    schema = yaml.safe_load(wrangles.recipe._recipe_wrangles.standardize.clean.__doc__)
    assert schema["properties"]["unescape_markdown"]["default"] is False
    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.validate(options, schema)
    source = r"$12\text{ VDC}$; \u0026 PART\_"
    frame = wrangles.DataFrame({"raw": [source, 42]})
    recipe_result = wrangles.recipe.run(
        {"wrangles": [{"standardize.clean": options}]}, dataframe=frame.copy(),
    )
    accessor_result = frame.wrangles.standardize.clean(**options)
    assert recipe_result.to_dict("list") == {
        "raw": [source, 42], "clean": ["12 VDC; & PART_", 42],
    }
    assert accessor_result.equals(recipe_result)


def test_markdown_unclosed_fence_is_preserved():
    source = "```\n" + r"A\_B"
    assert _clean(source, unescape_markdown=True) == source


def test_markdown_link_labels_clean_without_rewriting_destinations():
    source = r"[PART\_](https://example.com/a\_b) and A\_B"
    expected = r"[PART_](https://example.com/a\_b) and A_B"
    assert _clean(source, unescape_markdown=True) == expected


def test_markdown_long_prose_preserves_layout_and_mixed_values():
    source = "# Heading\n\n" + "x" * 40000 + "\n\n" + r"PART\_"
    expected = source[:-6] + "PART_"
    assert _clean([source, None, False, {"raw": r"A\_B"}], unescape_markdown=True) == [
        expected, None, False, {"raw": r"A\_B"},
    ]


@pytest.mark.parametrize("punctuation", ['"', "'", "$"])
def test_markdown_quotes_and_non_currency_dollars(punctuation):
    assert _clean("A\\" + punctuation + "B", unescape_markdown=True) == "A" + punctuation + "B"


def test_generated_recipe_schema_supports_markdown_toggle(tmp_path, monkeypatch):
    import json
    import runpy
    import shutil
    from pathlib import Path
    from types import SimpleNamespace
    import jsonschema
    import requests

    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(root / "schema/recipe_base_schema.json", tmp_path / "recipe_base_schema.json")
    monkeypatch.chdir(tmp_path)

    def schema_response(url):
        assert url == "http://json-schema.org/draft-07/schema#"
        return SimpleNamespace(json=lambda: jsonschema.Draft7Validator.META_SCHEMA)

    monkeypatch.setattr(requests, "get", schema_response)
    runpy.run_path(str(root / "schema/generate_recipe_schema.py"))
    generated = json.loads((tmp_path / "schema.json").read_text())
    contract = generated["$defs"]["wrangles"]["items"]["properties"]["standardize.clean"]
    assert contract["properties"]["unescape_markdown"] == {
        "type": "boolean", "default": False,
        "description": yaml.safe_load(
            wrangles.recipe._recipe_wrangles.standardize.clean.__doc__
        )["properties"]["unescape_markdown"]["description"],
    }
    jsonschema.Draft7Validator.check_schema(generated)
    jsonschema.validate({"wrangles": [{"standardize.clean": {
        "input": "raw", "unescape_markdown": True,
    }}]}, generated)


@pytest.mark.parametrize(("source", "options", "expected"), [
    (r"PART\_", {}, r"PART\_"),
    (r"PART\_", {"unescape_markdown": True}, "PART_"),
    (r"`PART\_`", {"unescape_markdown": True}, r"`PART\_`"),
    (r"C:\_cache\part", {"unescape_markdown": True}, r"C:\_cache\part"),
    (r"$12\text{ VDC}$ PART\_", {"unescape_markdown": True, "latex_to_text": True}, "12 VDC PART_"),
    (r"\u005c_", {"unescape_markdown": True, "unescape_unicode": True}, r"\_"),
])
def test_shared_escape_scanner_markdown_contract(source, options, expected):
    from wrangles._text_cleanup import clean_escaped_text

    assert clean_escaped_text(source, **options) == expected


@pytest.mark.parametrize(("source", "expected"), [
    (r"A\u0026B", "A&B"),
    (r"Temperature\u00b0C", "Temperature\N{DEGREE SIGN}C"),
    (r"A\U0001F600B", "A\N{GRINNING FACE}B"),
    (r"A\uD83D\uDE00B", "A\N{GRINNING FACE}B"),
])
def test_markdown_does_not_misclassify_unicode_prose_as_paths(source, expected):
    assert _clean(source, unescape_unicode=True, unescape_markdown=True) == expected
    assert _clean(source, unescape_unicode=True) == expected


@pytest.mark.parametrize("path", [
    r"C:\folder\file.txt", r"C:\folder", r"\\server\share\file.txt",
    r".\folder\file.txt", r"folder\part\_file.txt",
    r'"C:\Program Files\_cache\file.txt"',
    r"C:\Users\u0026\_data.txt",
])
@pytest.mark.parametrize("separator", [" and ", " then ", "; "])
def test_markdown_path_protection_stops_before_adjacent_prose(path, separator):
    source = path + separator + r"PART\_123 A\u0026B"
    assert _clean(source, unescape_unicode=True, unescape_markdown=True) == (
        path + separator + "PART_123 A&B"
    )


def test_markdown_and_unicode_escapes_in_same_unprefixed_token():
    assert _clean(r"A\u0026B\_C", unescape_unicode=True, unescape_markdown=True) == "A&B_C"


def test_recipe_cleans_unicode_and_prose_beside_protected_path():
    from wrangles._text_cleanup import clean_escaped_text

    source = r"C:\u0026\_cache and A\u0026B PART\_123"
    expected = r"C:\u0026\_cache and A&B PART_123"
    assert clean_escaped_text(
        source, unescape_unicode=True, unescape_markdown=True,
    ) == expected
    result = wrangles.recipe.run(
        {"wrangles": [{"standardize.clean": {
            "input": "raw", "output": "clean",
            "unescape_unicode": True, "unescape_markdown": True,
            "collapse_whitespace": False, "trim": False,
        }}]},
        dataframe=pd.DataFrame({"raw": [source]}),
    )
    assert result.to_dict("list") == {"raw": [source], "clean": [expected]}


@pytest.mark.parametrize("prefix", [r"\\server\shared files\_part.txt", r".\shared files\_part.txt", r"..\shared files\_part.txt"])
@pytest.mark.parametrize("quote", ['"', "'"])
@pytest.mark.parametrize("other_options", [False, True])
def test_markdown_preserves_quoted_unc_and_relative_paths(prefix, quote, other_options):
    path = quote + prefix + quote
    assert _clean(
        path + r" and PART\_", unescape_markdown=True,
        unescape_unicode=other_options, latex_to_text=other_options,
    ) == path + " and PART_"


@pytest.mark.parametrize(("source", "expected"), [
    (r"A\_B\u0026C", "A_B&C"),
    (r"A\_B\U0001F600C", "A_B\N{GRINNING FACE}C"),
    (r"A\_B\uD83D\uDE00C", "A_B\N{GRINNING FACE}C"),
    (r"folder\part\u0026C", r"folder\part&C"),
])
def test_markdown_before_unicode_does_not_establish_a_relative_path(source, expected):
    assert _clean(source, unescape_unicode=True, unescape_markdown=True) == expected


@pytest.mark.parametrize(("source", "expected"), [
    (r"($12\text{ VDC}$)", "(12 VDC)"),
    (r"Output:$12\text{VDC}$", "Output:12VDC"),
    (r"Output:$12\text{VDC}$ PART\_", "Output:12VDC PART_"),
    (r"prefix$\unknown{A\_B}$", r"prefix$\unknown{A\_B}$"),
])
def test_markdown_path_candidates_do_not_swallow_adjacent_math(source, expected):
    assert _clean(source, latex_to_text=True, unescape_markdown=True) == expected


@pytest.mark.parametrize("delimiters", [(r"\[", r"\]"), (r"\(", r"\)")])
@pytest.mark.parametrize("indent", ["", "    ", "\t"])
@pytest.mark.parametrize("latex_to_text", [False, True])
def test_markdown_preserves_multiline_unsupported_tex(delimiters, indent, latex_to_text):
    formula = delimiters[0] + "\n" + indent + r"x^2 + y_1 \times 2" + "\n" + delimiters[1]
    source = formula + "\n\n" + r"PART\_"
    assert _clean(source, unescape_markdown=True, latex_to_text=latex_to_text) == formula + "\n\nPART_"


def test_recipe_preserves_quoted_paths_and_math_while_cleaning_mixed_escapes():
    source = [
        r'"\\server\shared files\_part.txt" and PART\_',
        r"A\_B\u0026C",
        r"Output:$12\text{VDC}$",
        "\\[\n    x^2 + y_1\n\\]",
    ]
    expected = [
        r'"\\server\shared files\_part.txt" and PART_',
        "A_B&C", "Output:12VDC", source[3],
    ]
    result = wrangles.recipe.run(
        {"wrangles": [{"standardize.clean": {
            "input": "raw", "output": "clean",
            "unescape_unicode": True, "latex_to_text": True, "unescape_markdown": True,
            "collapse_whitespace": False, "trim": False,
        }}]},
        dataframe=pd.DataFrame({"raw": source}),
    )
    assert result.to_dict("list") == {"raw": source, "clean": expected}


def test_markdown_punctuation_rich_prose_scales_by_token_length():
    import time
    from wrangles._text_cleanup import clean_escaped_text

    timings = []
    for repeats in [4000, 16000]:
        source = "A-" * repeats
        start = time.process_time()
        assert clean_escaped_text(source, unescape_markdown=True) == source
        timings.append(time.process_time() - start)

    # Four times the input allows eight times the CPU plus scheduling/clock
    # slack, while rejecting the former roughly sixteenfold quadratic growth.
    assert timings[1] <= 8 * timings[0] + 0.05, timings
