"""
Test generic run behavior.

Tests specific to an individual connector should go 
in a test file for the respective connectors
e.g. tests/connectors/test_notifications.py
"""
import pathlib
import pandas as pd
import wrangles
import pytest
from wrangles.connectors import memory


def test_on_success():
    """
    Testing on success action is triggered correctly when finished
    """
    data = pd.DataFrame({
        'col1': ['hello world'],
    })
    success_rec = """
    write:
      - file:
          name: tests/temp/temp2.csv
    """
    recipe = """
    run:
      on_success:
        - recipe:
            name: ${rec2}
    wrangles:
      - convert.case:
          input: col1
          output: out1
          case: upper
    """
    vars = {
        "rec2": success_rec
    }
    df = wrangles.recipe.run(recipe, dataframe=data, variables=vars)
    assert df.iloc[0]['out1'] == 'HELLO WORLD'

def test_on_failure():
    """
    Testing on failure action is triggered correctly
    """
    data = pd.DataFrame({
        'col1': ['hello world'],
    })
    failure_rec = """
    write:
      - file:
          name: tests/temp/temp3.csv
    """
    recipe = """
    run:
      on_failure:
        - recipe:
            name: ${rec2}
    wrangles:
        - convert.case:
            input: col111
            output: out
            case: upper
    """
    vars = {
        "rec2": failure_rec
    }
    with pytest.raises(KeyError) as info:
        wrangles.recipe.run(recipe, dataframe=data, variables=vars)
    assert (
        info.typename == 'KeyError' and
        "Column col111" in info.value.args[0]
    )

def test_if_false():
    """
    Test that a run action is not triggered
    when an if statement is false
    """
    wrangles.recipe.run(
        """
        run:
          on_start:
            - recipe:
                if: 1 == 2
                read:
                - test:
                    rows: 1
                    values:
                        header: value
                write:
                - memory:
                    id: run_if_should_not_run
        """
    )
    assert "run_if_should_not_run" not in wrangles.connectors.memory.dataframes

def test_if_true():
    """
    Test that run action is triggered
    when an if statement is true
    """
    wrangles.recipe.run(
        """
        run:
          on_start:
            - recipe:
                if: 1 == 1
                read:
                - test:
                    rows: 1
                    values:
                        header: value
                write:
                - memory:
                    id: run_if_should_run
        """
    )
    assert "run_if_should_run" in wrangles.connectors.memory.dataframes

def test_if_variables_syntax():
    """
    Test that an if statement runs correctly
    when using variables using the syntax ${var}
    """
    wrangles.recipe.run(
        """
        run:
          on_start:
            - recipe:
                if: ${var} == 1
                read:
                  - test:
                      rows: 1
                      values:
                        header: value
                write:
                  - memory:
                      id: run_if_variables_syntax_should_run
        """,
        variables={
            "var": 1
        }
    )

    assert "run_if_variables_syntax_should_run" in wrangles.connectors.memory.dataframes

def test_overwrite_run():
    """
    Test overwriting a stock run with a custom function
    """
    check_var = {}

    class notification:
        def run(key):
            check_var[key] = True

    wrangles.recipe.run(
        """
        run:
          on_start:
            - notification:
                key: value
        """,
        functions=notification
    )

    assert check_var.get("value") is True


def test_run_path_object():
    """
    Test that recipe.run accepts a pathlib.Path to a YAML file (issue #986)
    """
    df = wrangles.recipe.run(pathlib.Path('tests/samples/recipe-basic.wrgl.yml'))
    assert list(df.columns) == ['header1', 'header2']


def test_run_pure_posix_path():
    """
    Test that recipe.run accepts a pathlib.PurePosixPath (issue #986)
    """
    df = wrangles.recipe.run(pathlib.PurePosixPath('tests/samples/recipe-basic.wrgl.yml'))
    assert list(df.columns) == ['header1', 'header2']


def _make_reference():
    return {
        "file_id": "file-123",
        "meta": {
            "bucket": "docs",
            "tags": ["a", "b"]
        },
        "nullable": None
    }


def test_runtime_result_variable_and_late_resolution():
    """
    Action results can be captured and consumed via runtime references.
    """
    df = wrangles.recipe.run(
        """
        run:
          on_start:
            - custom._make_reference:
                result_variable: upload_ref
        wrangles:
          - create.column:
              output: file_id
              value: ${runtime.upload_ref.file_id}
          - create.column:
              output: metadata
              value: ${runtime.upload_ref.meta}
          - create.column:
              output: nullable
              value: ${runtime.upload_ref.nullable}
        """,
        dataframe=pd.DataFrame({"row": [1]}),
        functions=_make_reference
    )
    assert df["file_id"][0] == "file-123"
    assert df["metadata"][0] == {"bucket": "docs", "tags": ["a", "b"]}
    assert df["nullable"][0] == ""


def test_runtime_set_update_and_condition():
    """
    Runtime variables can be set, updated and used in conditions.
    """
    df = wrangles.recipe.run(
        """
        run:
          on_start:
            - variables:
                set:
                  runtime_state:
                    retry: 0
                  run_mode: active
            - variables:
                update:
                  runtime_state:
                    retry: 1
                    nested:
                      value: done
        wrangles:
          - create.column:
              output: retry
              value: ${runtime.runtime_state.retry}
              if: ${runtime.run_mode} == "active"
          - create.column:
              output: nested
              value: ${runtime.runtime_state.nested}
        """,
        dataframe=pd.DataFrame({"row": [1]})
    )
    assert df["retry"][0] == 1
    assert df["nested"][0] == {"value": "done"}


def test_runtime_reference_without_dataframe():
    """
    Runtime variables are usable even when recipe starts without a dataframe.
    """
    captured = []

    def capture_value(value):
        captured.append(value)

    wrangles.recipe.run(
        """
        run:
          on_start:
            - variables:
                set:
                  startup_value: ready
          on_success:
            - custom.capture_value:
                value: ${runtime.startup_value}
        """,
        functions=capture_value
    )
    assert captured == ["ready"]


def test_runtime_variable_assignment_protects_reserved_names():
    with pytest.raises(ValueError, match="protected"):
        wrangles.recipe.run(
            """
            run:
              on_start:
                - variables:
                    set:
                      row_count: 10
            """
        )


def test_runtime_missing_variable_and_escaped_literal(caplog):
    with pytest.raises(ValueError, match="Runtime variable '\\$\\{runtime.missing\\}' was not found"):
        wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 1
                  values:
                    header: value
            wrangles:
              - create.column:
                  output: out
                  value: ${runtime.missing}
            """
        )

    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: value
        wrangles:
          - log:
              info: '\\${runtime.literal_value}'
              log_data: false
        """
    )
    assert "${runtime.literal_value}" in caplog.messages


def test_runtime_nested_export_and_conflict_policy():
    """
    Nested recipes receive a snapshot and only export back explicitly.
    """
    df = wrangles.recipe.run(
        """
        run:
          on_start:
            - variables:
                set:
                  parent_flag: parent
            - recipe:
                run:
                  on_start:
                    - variables:
                        set:
                          parent_flag: child
                          child_export: exported
                export_runtime_variables:
                  - child_export
        wrangles:
          - create.column:
              output: parent_flag
              value: ${runtime.parent_flag}
          - create.column:
              output: child_export
              value: ${runtime.child_export}
        """,
        dataframe=pd.DataFrame({"row": [1]})
    )
    assert df["parent_flag"][0] == "parent"
    assert df["child_export"][0] == "exported"

    with pytest.raises(ValueError, match="Runtime export collision"):
        wrangles.recipe.run(
            """
            run:
              on_start:
                - variables:
                    set:
                      parent_flag: parent
                - recipe:
                    run:
                      on_start:
                        - variables:
                            set:
                              parent_flag: child
                    export_runtime_variables:
                      - parent_flag
            """
        )

    df_overwrite = wrangles.recipe.run(
        """
        run:
          on_start:
            - variables:
                set:
                  parent_flag: parent
            - recipe:
                run:
                  on_start:
                    - variables:
                        set:
                          parent_flag: child
                export_runtime_variables:
                  - parent_flag
                export_conflict_policy: overwrite
        wrangles:
          - create.column:
              output: parent_flag
              value: ${runtime.parent_flag}
        """,
        dataframe=pd.DataFrame({"row": [1]})
    )
    assert df_overwrite["parent_flag"][0] == "child"


def test_runtime_inspection_redacts_sensitive_values_and_bounds_output(caplog):
    wrangles.recipe.run(
        """
        run:
          on_start:
            - variables:
                set:
                  access_token: abc123
                  signed_url: https://example.com/file?X-Amz-Signature=secret&X-Amz-Credential=cred
                  safe_info:
                    rows:
                      - 1
                      - 2
                      - 3
                      - 4
                mark_secret:
                  - signed_url
                inspect:
                  - access_token
                  - signed_url
                  - safe_info
                max_items: 2
        """
    )
    message = "\n".join(caplog.messages)
    assert "[REDACTED]" in message
    assert "2 more item(s)" in message


def test_log_wrangle_runtime_variables(caplog):
    wrangles.recipe.run(
        """
        run:
          on_start:
            - variables:
                set:
                  upload_ref:
                    file_id: file-123
        read:
          - test:
              rows: 1
              values:
                col1: value
        wrangles:
          - log:
              runtime_variables:
                - upload_ref.file_id
              log_data: false
        """
    )

    assert "upload_ref.file_id" in "\n".join(caplog.messages)


def test_runtime_variables_do_not_mutate_caller_input_dict():
    variables = {
        "mutable_settings": {
            "value": "original"
        }
    }

    wrangles.recipe.run(
        """
        run:
          on_start:
            - variables:
                update:
                  mutable_settings:
                    value: changed
        """,
        variables=variables
    )

    assert variables["mutable_settings"]["value"] == "original"


def test_runtime_parallel_branches_are_isolated():
    observed = []

    def capture_branch(value):
        observed.append(value)

    wrangles.recipe.run(
        """
        run:
          on_start:
            - concurrent:
                run:
                  - recipe:
                      run:
                        on_start:
                          - variables:
                              set:
                                branch_value: 1
                          - custom.capture_branch:
                              value: ${runtime.branch_value}
                  - recipe:
                      run:
                        on_start:
                          - variables:
                              set:
                                branch_value: 2
                          - custom.capture_branch:
                              value: ${runtime.branch_value}
        """,
        functions=capture_branch
    )

    assert sorted(observed) == [1, 2]


def test_runtime_references_in_read_write_and_if():
    memory.clear()
    memory.dataframes["runtime_source"] = pd.DataFrame({"value": ["ok"]})

    wrangles.recipe.run(
        """
        run:
          on_start:
            - variables:
                set:
                  source_id: runtime_source
                  target_id: runtime_target
                  should_write: true
        read:
          - memory:
              id: ${runtime.source_id}
        write:
          - memory:
              id: ${runtime.target_id}
              if: ${runtime.should_write} == True
        """
    )

    assert "runtime_target" in memory.dataframes
    assert memory.dataframes["runtime_target"]["data"][0][0] == "ok"
