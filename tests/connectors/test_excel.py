import wrangles


def test_excel():
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
                header2: value2
        
        write:
          - excel: {}
        """
    )

    data = wrangles.connectors.excel.stored_dfs
    assert (
        data[0]["columns"] == ["header1", "header2"] and
        len(data[0]["values"]) == 5
    )

def test_excel_args():
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
                header2: value2
        
        write:
          - excel:
              sheet: test
              row: 5
        """
    )

    data = wrangles.connectors.excel.stored_dfs
    assert (
        data[0]["columns"] == ["header1", "header2"] and
        data[0]["sheet"] == "test" and
        data[0]["row"] == 5
    )

def test_excel_multiple():
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
                header2: value2
        
        write:
          - excel:
              sheet: test1

          - excel:
              sheet: test2
        """
    )

    data = wrangles.connectors.excel.stored_dfs
    assert (
        data[0]["columns"] == ["header1", "header2"] and
        data[0]["sheet"] == "test1" and
        data[1]["columns"] == ["header1", "header2"] and
        data[1]["sheet"] == "test2"
    )
