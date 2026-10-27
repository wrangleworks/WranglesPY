"""Direct regressions for clean_whitespaces Unicode normalization (#1242)."""
import unicodedata

import pandas as pd
import pytest
import wrangles

from wrangles.recipe_wrangles.main import clean_whitespaces


WHITESPACE = [chr(code) for code in range(0x3100) if chr(code).isspace()]
SPACE_SEPARATORS = [char for char in WHITESPACE if unicodedata.category(char) == "Zs"]
LINE_CONTROLS = [char for char in WHITESPACE if char not in SPACE_SEPARATORS]


@pytest.mark.parametrize("separator", WHITESPACE, ids=ascii)
@pytest.mark.parametrize("count", [1, 3])
def test_default_normalizes_unicode_whitespace(separator, count):
    df = pd.DataFrame({"text": ["A" + separator * count + "B"]})

    result = clean_whitespaces(df, "text")

    assert result["text"].tolist() == ["A B"]


@pytest.mark.parametrize("remove_literals", [True, False])
def test_mixed_spaces_and_u0081_collapse_together(remove_literals):
    df = pd.DataFrame({"text": ["A \u0081\u2007\u00a0\u202f B", "A\u0081B"]})

    result = clean_whitespaces(df, "text", remove_literals=remove_literals)

    assert result["text"].tolist() == ["A B", "A B"]


@pytest.mark.parametrize("separator", SPACE_SEPARATORS, ids=ascii)
@pytest.mark.parametrize("count", [1, 3])
def test_remove_literals_false_normalizes_unicode_spaces(separator, count):
    df = pd.DataFrame({"text": ["A" + separator * count + "B"]})

    result = clean_whitespaces(df, "text", remove_literals=False)

    assert result["text"].tolist() == ["A B"]


@pytest.mark.parametrize("separator", LINE_CONTROLS, ids=ascii)
def test_remove_literals_false_preserves_internal_controls(separator):
    text = "A" + separator * 2 + "B"
    df = pd.DataFrame({"text": [text, "A\u2009\t\r\n\u2028\u2029\u3000B"]})

    result = clean_whitespaces(df, "text", remove_literals=False)

    assert result["text"].tolist() == [text, "A \t\r\n\u2028\u2029 B"]


@pytest.mark.parametrize("remove_literals", [True, False])
@pytest.mark.parametrize("trim", [True, False])
def test_trim_and_column_mapping(remove_literals, trim):
    source = pd.DataFrame({"first": ["\u2009A\u202fB\u3000"], 7: ["\u0081C  D\u0081"]})
    original = source.copy(deep=True)

    result = clean_whitespaces(
        source, ["first", 7], ["out1", "out2"], trim=trim,
        remove_literals=remove_literals,
    )

    pd.testing.assert_frame_equal(result[["first", 7]], original)
    assert result[["out1", "out2"]].values.tolist() == (
        [["A B", "C D"]] if trim else [[" A B ", " C D "]]
    )


def test_remove_literals_false_still_trims_boundary_controls():
    result = clean_whitespaces(
        pd.DataFrame({"text": ["\t\nA\tB\r\n"]}), "text", remove_literals=False,
    )

    assert result["text"].tolist() == ["A\tB"]


@pytest.mark.parametrize("remove_literals", [True, False])
def test_empty_and_non_string_values_are_preserved(remove_literals):
    values = ["", None, 123, 45.67, True, ["A\nB"], {"text": "A\nB"}]
    source = pd.DataFrame({"text": pd.Series(values, dtype=object)})

    result = clean_whitespaces(source.copy(deep=True), "text", remove_literals=remove_literals)

    pd.testing.assert_frame_equal(result, source)
    empty = pd.DataFrame({"text": pd.Series(dtype=object)})
    pd.testing.assert_frame_equal(
        clean_whitespaces(empty.copy(), "text", remove_literals=remove_literals), empty,
    )


@pytest.mark.parametrize("remove_literals", [True, False])
def test_unrelated_text_and_duplicate_rows_are_preserved(remove_literals):
    text = r"A\nB &nbsp; &#160;" + "\u200b\u200c\u200d\ufeff"
    source = pd.DataFrame({"text": [text, text]})

    result = clean_whitespaces(source.copy(), "text", remove_literals=remove_literals)

    pd.testing.assert_frame_equal(result, source)


def test_recipe_normalizes_actual_newline():
    result = wrangles.recipe.run(
        {"wrangles": [{"clean_whitespaces": {"input": "text", "output": "normalized"}}]},
        dataframe=pd.DataFrame({"text": ["A\nB"]}),
    )

    assert result.to_dict("list") == {"text": ["A\nB"], "normalized": ["A B"]}
