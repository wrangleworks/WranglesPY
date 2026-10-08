import wrangles
import pandas as pd
import pytest

def test_read():
    """
    Test an unmodified read
    """
    df = wrangles.recipe.run(
        """
        read:
          - input
        """,
        dataframe=pd.DataFrame({"header": ["value"]})
    )
    assert df["header"][0] == "value"

def test_read_columns():
    """
    Test that only the specified columns are read
    """
    df = wrangles.recipe.run(
        """
        read:
          - input:
              columns: header1
        """,
        dataframe=pd.DataFrame({
            "header1": ["value1"],
            "header2": ["value2"]
        })
    )
    assert df.columns.tolist() == ["header1"] and df["header1"][0] == "value1"

def test_read_where():
    """
    Test a read with a where
    """
    df = wrangles.recipe.run(
        """
        read:
          - input:
              where: idx < 2
        """,
        dataframe=pd.DataFrame({
            "idx": [0, 1, 2],
            "header1": ["a", "b", "c"],
            "header2": [1,2,3]
        })
    )
    assert (
        df.columns.tolist() == ["idx", "header1", "header2"] and
        df["header1"][0] == "a" and
        len(df) == 2
    )

def test_read_union():
    """
    Test as part of a union
    """
    df = wrangles.recipe.run(
        """
        read:
          - union:
              sources:
                - test:
                    rows: 1
                    values:
                      idx: 0
                      header1: a
                - input
        """,
        dataframe=pd.DataFrame({
            "idx": [1, 2, 3],
            "header1": ["b", "c", "d"],
        })
    )
    assert (
        df.columns.tolist() == ["idx", "header1"] and
        df["header1"].values.tolist() == ["a", "b", "c", "d"] and
        len(df) == 4
    )


@pytest.mark.parametrize('connector', ['grid.selected_data', 'excel.selected_data'])
def test_selected_data_filters_current_batch_without_mutating_input(connector):
    batch = pd.DataFrame({'ID': [3, 4], 'Value': ['c', 'd']})
    result = wrangles.recipe.run(
        {'read': {connector: {'columns': ['Value'], 'where': 'ID = 4'}}},
        dataframe=batch,
    )
    assert result.to_dict('list') == {'Value': ['d']}
    assert batch.to_dict('list') == {'ID': [3, 4], 'Value': ['c', 'd']}


@pytest.mark.parametrize('connector', ['input', 'grid.selected_data', 'excel.selected_data'])
@pytest.mark.parametrize('composition', ['union', 'join', 'concatenate'])
@pytest.mark.parametrize('data', [None, pd.DataFrame(columns=['ID'])])
def test_composed_selected_data_rejects_missing_and_empty(connector, composition, data):
    params = {'sources': [{connector: {}}, {'test': {'rows': 1, 'values': {'ID': 1}}}]}
    if composition == 'join':
        params['on'] = 'ID'
    with pytest.raises(ValueError, match='missing or empty'):
        wrangles.recipe.run({'read': {composition: params}}, dataframe=data)


@pytest.mark.parametrize('connector', ['input', 'grid.selected_data', 'excel.selected_data'])
def test_composed_selected_data_rejects_filter_removing_all_rows(connector):
    with pytest.raises(ValueError, match='empty after filtering'):
        wrangles.recipe.run(
            {'read': {'union': {'sources': [
                {connector: {'where': 'ID > 10'}},
                {'test': {'rows': 1, 'values': {'ID': 2}}},
            ]}}}, dataframe=pd.DataFrame({'ID': [1]}),
        )


def test_generic_input_still_allows_an_empty_dataframe_outside_composition():
    result = wrangles.recipe.run({'read': {'input': {}}}, dataframe=pd.DataFrame(columns=['ID']))
    assert result.empty and result.columns.tolist() == ['ID']


@pytest.mark.parametrize('connector', ['grid.selected_data', 'excel.selected_data'])
@pytest.mark.parametrize('saved', [False, True])
def test_nested_selected_data_reads_transformed_parent_dataframe(connector, saved, monkeypatch):
    child = {'read': {connector: {}}}
    if saved:
        monkeypatch.setattr(wrangles.data, 'model', lambda *_: {
            'purpose': 'recipe', 'name': 'Synthetic child',
        })
        monkeypatch.setattr(wrangles.data, 'model_content', lambda *_: {
            'recipe': f'read:\n  - {connector}: {{}}\n',
        })
        child = {'name': '12345678-abcd-abcd'}
    result = wrangles.recipe.run(
        {'wrangles': [
            {'convert.case': {'input': 'Value', 'case': 'upper'}},
            {'recipe': child},
        ]}, dataframe=pd.DataFrame({'ID': [3], 'Value': ['batch three']}),
    )
    assert result.to_dict('list') == {'ID': [3], 'Value': ['BATCH THREE']}


def test_empty_external_result_is_not_an_empty_selected_data_error():
    result = wrangles.recipe.run({'read': {'test': {'rows': 0, 'values': {'ID': 1}}}})
    assert result.empty


@pytest.mark.parametrize('connector', ['input', 'grid.selected_data', 'excel.selected_data'])
def test_mixed_read_uses_only_current_batch_ids(connector):
    # Synthetic lookup: the recipe author scopes the external query to the
    # current invocation's IDs. Excel does not batch or deduplicate its rows.
    catalog = pd.DataFrame({'ID': range(1, 6), 'Product': list('abcde')})
    requested_ids = []
    outputs = []
    for ids in ([1, 2], [3, 4], [5]):
        def query_products(ids):
            requested_ids.append(ids)
            return catalog[catalog.ID.isin(ids)].copy()

        outputs.append(wrangles.recipe.run(
            {'read': {'join': {'on': 'ID', 'how': 'left', 'sources': [
                {connector: {}},
                {'custom.query_products': {'ids': '${batch_ids}'}},
            ]}}},
            dataframe=pd.DataFrame({'ID': ids}),
            variables={'batch_ids': ids},
            functions=query_products,
        ))
    assert requested_ids == [[1, 2], [3, 4], [5]]
    assert pd.concat(outputs).to_dict('list') == catalog.to_dict('list')


def test_composed_read_allows_empty_external_source():
    result = wrangles.recipe.run(
        {'read': {'union': {'sources': [
            {'input': {}}, {'test': {'rows': 0, 'values': {'ID': 1}}},
        ]}}}, dataframe=pd.DataFrame({'ID': [7]}),
    )
    assert result.to_dict('list') == {'ID': [7]}


def test_generated_schema_exposes_shared_and_excel_selected_data(tmp_path, monkeypatch):
    import json
    import runpy
    from pathlib import Path
    import jsonschema

    root = Path(__file__).resolve().parents[2]
    (tmp_path / 'recipe_base_schema.json').write_text(
        (root / 'schema/recipe_base_schema.json').read_text(encoding='utf-8'),
        encoding='utf-8',
    )
    monkeypatch.chdir(tmp_path)
    runpy.run_path(str(root / 'schema/generate_recipe_schema.py'))
    schema = json.loads((tmp_path / 'schema.json').read_text(encoding='utf-8'))
    for connector in ['input', 'grid.selected_data', 'excel.selected_data']:
        jsonschema.validate({'read': [{connector: {'columns': ['ID']}}]}, schema)
    jsonschema.validate({'write': [{'excel.columns': {'columns': ['Result']}}]}, schema)
