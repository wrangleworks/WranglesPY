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
    (r"$\$6\text{ mm}$", "6 mm"),
    (r"$\$19\text{ mm}$", "19 mm"),
    (r"$\$12\text{ mm}$", "12 mm"),
    (r"$\$5400\text{ N}$", "5400 N"),
    (r"$\$8000\text{ N}$", "8000 N"),
    (r"$\$5.4\mathrm{ kN}$", "5.4 kN"),
    (r"$\$12\text{ VDC}$", "12 VDC"),
])
def test_latex_measurements_drop_stray_escaped_dollars(original, expected):
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
    (r"$\$6m$", "$6m"),
    ("$6 mm", "$6 mm"),
    (r"$\$6\unknown{ mm}$", r"$\$6\unknown{ mm}$"),
])
def test_latex_measurement_repair_preserves_currency_and_ambiguous_values(original, expected):
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


def test_trial_link_cleanup_changes_labels_only():
    from run_search_ai_mode import clean_ai_mode_links

    label = "PartGo to product viewer dialog for this item."
    url = r"https://www.google.com/search?prds=item(1)&q=product&raw=\u0026"
    raw = f"[{label}]({url})"
    code = f"`{raw}`\n\n```\n{raw}\n```"
    text = "Go to product viewer dialog for this item."
    data = pd.DataFrame({"original": [raw + "\n\n" + code + "\n\n" + text, None]})
    output = clean_ai_mode_links(data, input="original", output="clean")
    assert output.iloc[0]["original"].startswith(raw)
    assert output["clean"].tolist() == [
        f"[Part]({url})\n\n{code}\n\n{text}", None
    ]
