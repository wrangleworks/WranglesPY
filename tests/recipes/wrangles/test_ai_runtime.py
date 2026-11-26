"""Credential-free acceptance through the normal recipe entry point."""

import asyncio
import builtins
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pandas as pd
import pytest

import wrangles


OUTPUT = {"Name": {"type": "string"}, "Count": {"type": "integer"}}
ROWS = [{"row_id": 2, "Name": "Pump Seal", "Count": 2},
        {"row_id": 0, "Name": "Pump Seal", "Count": 2},
        {"row_id": 1, "Name": "Valve Kit", "Count": 1}]


@pytest.fixture(autouse=True)
def no_live_auth(monkeypatch):
    monkeypatch.setattr(wrangles.recipe._auth, "get_applied_permission_group", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture
def source():
    return pd.DataFrame({"Description": ["PUMP seal", "valve kit", "pump SEAL"],
                         "Unrelated": [7, 8, 9]}, index=[8, 3, 8])


@pytest.fixture
def package(tmp_path):
    manifest = {"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json", "name": "test-products"}
    (tmp_path / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    path = tmp_path / "skills" / "normalize-products" / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text("---\nname: normalize-products\ndescription: Normalize product names\n---\n"
                    "Title-case Description into Name. Count matching normalized names across all rows into Count.",
                    encoding="utf-8")
    return str(tmp_path)


@pytest.fixture
def sdk(monkeypatch):
    session = SimpleNamespace(send_and_wait=AsyncMock(), disconnect=AsyncMock())
    client = SimpleNamespace(start=AsyncMock(), create_session=AsyncMock(return_value=session),
                             stop=AsyncMock(), force_stop=AsyncMock())
    factory = Mock(return_value=client)
    connection = Mock(side_effect=lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setitem(sys.modules, "copilot", SimpleNamespace(CopilotClient=factory, SkillProviderDescriptor=SimpleNamespace,
        RuntimeConnection=SimpleNamespace(for_spawned_stdio=connection)))
    monkeypatch.setitem(sys.modules, "copilot.tools", SimpleNamespace(
        Tool=lambda **kwargs: SimpleNamespace(**kwargs),
        ToolResult=lambda **kwargs: SimpleNamespace(**kwargs)))
    monkeypatch.setitem(sys.modules, "copilot.rpc", SimpleNamespace(PermissionDecisionReject=lambda: "denied"))
    state = SimpleNamespace(client=client, session=session, factory=factory, connection=connection, read=None,
                            submitted=None, actions=[], replies=[], response={"rows": ROWS})

    async def execute(*args, **kwargs):
        tools = {tool.name: tool for tool in client.create_session.call_args.kwargs["tools"]["definitions"]}
        state.read = json.loads((await tools["read_dataframe"].handler(SimpleNamespace(arguments={}))).text_result_for_llm)
        for name, arguments in state.actions:
            state.replies.append(await tools[name].handler(SimpleNamespace(arguments=arguments)))
        state.submitted = await tools["submit_results"].handler(SimpleNamespace(arguments=state.response))
    session.send_and_wait.side_effect = execute
    return state


def run(source, kind="agent", **kwargs):
    options = {"input": "Description", "output": OUTPUT, "api_key": "offline-key", **kwargs}
    if kind == "agent":
        options.setdefault("instructions", "Normalize names and count matching names across all supplied rows.")
    return wrangles.recipe.run({"wrangles": [{"ai." + kind: options}]}, dataframe=source)


@pytest.mark.parametrize("kind,attach", [("agent", False), ("agent", True), ("skill", True)])
def test_recipe_acceptance_preserves_identity_and_unrelated_columns(source, package, sdk, kind, attach):
    original = source.copy(deep=True)
    result = run(source, kind, **({"skill": "normalize-products", "skill_package": package} if attach else {}))
    assert result["Name"].tolist() == ["Pump Seal", "Valve Kit", "Pump Seal"]
    assert result["Count"].tolist() == [2, 1, 2]
    pd.testing.assert_frame_equal(result[original.columns], original)
    pd.testing.assert_frame_equal(source, original)
    assert sdk.read == {"rows": [{"row_id": 0, "Description": "PUMP seal"},
                                 {"row_id": 1, "Description": "valve kit"},
                                 {"row_id": 2, "Description": "pump SEAL"}]}
    config = sdk.client.create_session.call_args.kwargs
    assert config["model"] == "openai/gpt-5-mini"
    assert config["inference"]["providers"][0]["api_key"] == "offline-key"
    assert config["github"]["capi"] == {"enabled": False}
    assert config["tools"]["available_tools"] == [
        "custom:read_dataframe", "custom:convert_case", "custom:count_values", "custom:submit_results"]
    assert config["permissions"]["on_request"]({}, {}) == "denied"
    assert sdk.factory.call_args.kwargs["mode"] == "empty"
    assert sdk.factory.call_args.kwargs["github"] == {"use_logged_in_user": False}
    assert not Path(sdk.connection.call_args.kwargs["base_directory"]).exists()
    assert result.attrs["wrangles_ai_runtime"]["tools"] == ["read_dataframe", "submit_results"]
    if attach:
        assert result.attrs["wrangles_ai_runtime"]["skill"]["name"] == "normalize-products"
        assert result.attrs["wrangles_ai_runtime"]["skill"]["package"] == "test-products"
        provider = config["skills"]["provider"]
        assert config["agents"]["definitions"][0]["skills"] == ["normalize-products"]
        assert "Title-case Description" in provider.read_skill("normalize-products")
        assert [s.name for s in provider.list_skills()] == ["normalize-products"]
        assert provider.read_skill("another-skill") is None
    else:
        assert result.attrs["wrangles_ai_runtime"]["skill"] is None
        assert config["skills"] == {"enabled": False}
    sdk.session.disconnect.assert_awaited_once()
    sdk.client.stop.assert_awaited_once()


CASE_AND_COUNT = [
    ("convert_case", {"source": "Description", "destination": "Name", "case": "title"}),
    ("count_values", {"source": "Name", "destination": "Count"}),
]


@pytest.mark.parametrize("kind", ["agent", "skill"])
def test_python_count_wins_over_conflicting_model_submission(source, sdk, package, kind):
    sdk.actions = CASE_AND_COUNT
    # Duplicate input index labels, and the model submits rows out of order.
    sdk.response = {"rows": [{**r, "Count": 3, "Name": "model echo", "Reviewed": r["row_id"] != 1} for r in ROWS]}
    result = run(source, kind, skill="normalize-products", skill_package=package,
                 output={**OUTPUT, "Reviewed": {"type": "boolean"}})
    assert result["Count"].tolist() == [2, 1, 2]
    assert result["Name"].tolist() == ["Pump Seal", "Valve Kit", "Pump Seal"]
    assert result["Reviewed"].tolist() == [True, False, True]
    pd.testing.assert_frame_equal(result[source.columns], source)
    assert result.attrs["wrangles_ai_runtime"]["committed_columns"] == ["Name", "Count"]


def test_finish_without_echoing_python_columns(source, sdk):
    sdk.actions = CASE_AND_COUNT
    sdk.response = {}
    result = run(source)
    assert result["Count"].tolist() == [2, 1, 2]
    assert result.attrs["wrangles_ai_runtime"]["tools"] == ["read_dataframe", "convert_case", "count_values", "submit_results"]


def test_python_counts_model_judged_groups_by_position(source, sdk):
    sdk.actions = [("count_values", {"source": "Group", "destination": "Count", "source_rows": [
        {"row_id": 2, "value": "seal"}, {"row_id": 0, "value": "seal"}, {"row_id": 1, "value": "valve"}]})]
    sdk.response = {"rows": [{"row_id": i, "Group": "incorrect echo", "Count": 3} for i in range(3)]}
    result = run(source, output={"Group": {"type": "string"}, "Count": {"type": "integer"}})
    assert result["Group"].tolist() == ["seal", "valve", "seal"]
    assert result["Count"].tolist() == [2, 1, 2]


@pytest.mark.parametrize("bad_args", [
    {"source": "Unrelated", "destination": "Count"},
    {"source": "Description", "destination": "Unrelated"},
    {"source": "Description", "destination": "Count", "source_rows": []},
    {"source": "Name", "destination": "Count", "source_rows": [{"row_id": 0, "value": "x"}] * 3},
])
def test_rejected_tools_leave_columns_uncommitted(source, sdk, bad_args):
    sdk.actions = [("count_values", bad_args)]
    result = run(source)
    assert sdk.replies[0].result_type == "failure"
    assert result.attrs["wrangles_ai_runtime"]["committed_columns"] == []


def test_computed_column_cannot_be_replaced_by_another_tool(source, sdk):
    sdk.actions = [*CASE_AND_COUNT, ("count_values", {"source": "Description", "destination": "Count"})]
    sdk.response = {}
    result = run(source)
    assert sdk.replies[-1].result_type == "failure"
    assert result["Count"].tolist() == [2, 1, 2]


def test_multiple_native_skills_and_configured_package(source, package, sdk, monkeypatch):
    monkeypatch.setenv("WRANGLES_AGENT_PLUGIN", package)
    other = Path(package) / "skills" / "second" / "SKILL.md"
    other.parent.mkdir()
    other.write_text("---\nname: second\ndescription: Other rules\n---\nKeep original IDs.", encoding="utf-8")
    result = run(source, skills=[{"model_id": "normalize-products"}, {"model_id": "second"}])
    config = sdk.client.create_session.call_args.kwargs
    assert [s.name for s in config["skills"]["provider"].list_skills()] == ["normalize-products", "second"]
    assert config["agents"]["definitions"][0]["skills"] == ["normalize-products", "second"]
    assert [item["name"] for item in result.attrs["wrangles_ai_runtime"]["skills"]] == ["normalize-products", "second"]
    assert len(result.attrs["wrangles_ai_runtime"]["skills"][0]["sha256"]) == 64
    assert run(source, "skill", model_id="second").attrs["wrangles_ai_runtime"]["skill"]["name"] == "second"


@pytest.mark.parametrize("bad", [{"name": "test-products"}, {"$schema": "wrong", "name": "test-products"},
    {"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json", "name": "bad--name"},
    {"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json", "name": "valid", "author": []}])
def test_reject_invalid_portable_manifest_before_inference(package, source, sdk, bad):
    (Path(package) / "plugin.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(Exception, match="Invalid Agent Plugins 1.0 manifest"):
        run(source, "skill", model_id="normalize-products", skill_package=package)
    sdk.client.start.assert_not_awaited()


def test_python_api_from_running_event_loop(source, sdk):
    async def notebook():
        return wrangles.ai.agent(source, input="Description", instructions="Normalize", output=OUTPUT,
                                 api_key="offline-key")
    sdk.actions = CASE_AND_COUNT
    sdk.response = {}
    assert asyncio.run(notebook())["Count"].tolist() == [2, 1, 2]


@pytest.mark.parametrize("response", [None, {}, {"rows": []}, {"rows": ROWS[:2]},
    {"rows": [ROWS[0], ROWS[0], ROWS[1]]},
    {"rows": [{**row, "row_id": 9} for row in ROWS]},
    {"rows": [{**row, "Count": True} for row in ROWS]},
    {"rows": [{**row, "Count": "2"} for row in ROWS]},
    {"rows": [{**row, "Count": 2.0} for row in ROWS]},
    {"rows": [{**row, "Name": None} for row in ROWS]},
    {"rows": [{**row, "extra": "unexpected"} for row in ROWS]},
    {"rows": [{"row_id": i, "Name": "Pump"} for i in range(3)]},
    {"rows": [{**row, "row_id": True} for row in ROWS]},
])
def test_malformed_or_incomplete_results_fail_atomically(source, sdk, response):
    sdk.response = response
    with pytest.raises(Exception, match="did not submit a complete typed result"):
        run(source)
    assert source.columns.tolist() == ["Description", "Unrelated"]
    assert source["Unrelated"].tolist() == [7, 8, 9]
    sdk.session.disconnect.assert_awaited_once()
    sdk.client.stop.assert_awaited_once()


def test_no_tool_submission_rejects_prose(source, sdk):
    sdk.session.send_and_wait.side_effect = None
    sdk.session.send_and_wait.return_value = SimpleNamespace(data=SimpleNamespace(content="Done!"))
    with pytest.raises(Exception, match="did not submit"):
        run(source)
    sdk.session.disconnect.assert_awaited_once()
    sdk.client.stop.assert_awaited_once()


@pytest.mark.parametrize("stage", ["start", "create", "send", "disconnect", "stop"])
def test_runtime_errors_cleanup_and_redact(source, sdk, stage):
    target = {"start": sdk.client.start, "create": sdk.client.create_session,
              "send": sdk.session.send_and_wait, "disconnect": sdk.session.disconnect,
              "stop": sdk.client.stop}[stage]
    target.side_effect = RuntimeError("secret-provider-header")
    with pytest.raises(Exception) as error:
        run(source)
    assert "secret-provider-header" not in str(error.value)
    sdk.client.stop.assert_awaited_once()
    assert sdk.session.disconnect.await_count == (0 if stage in {"start", "create"} else 1)
    assert sdk.client.force_stop.await_count == (1 if stage == "stop" else 0)
    assert not Path(sdk.connection.call_args.kwargs["base_directory"]).exists()


def test_timeout_cancels_work_and_stops_runtime(source, sdk):
    cancelled = []
    async def hang(*args, **kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)
    sdk.session.send_and_wait.side_effect = hang
    with pytest.raises(Exception, match="exceeded timeout"):
        run(source, timeout=0.02)
    assert cancelled == [True]
    sdk.session.disconnect.assert_awaited_once()
    sdk.client.stop.assert_awaited_once()


@pytest.mark.parametrize("name", ["missing", "../normalize-products", "/absolute", "Bad Name"])
def test_skill_resolution_failure_never_starts_runtime(source, package, sdk, name):
    with pytest.raises(Exception):
        run(source, "skill", skill=name, skill_package=package)
    sdk.factory.assert_not_called()


@pytest.mark.parametrize("file,content", [("plugin.json", "[]"), ("plugin.json", "not json"),
    ("skills/normalize-products/SKILL.md", "no front matter"),
    ("skills/normalize-products/SKILL.md", "---\nname: other\ndescription: x\n---\nInstructions")])
def test_malformed_skill_package_fails_before_runtime(source, package, sdk, file, content):
    (Path(package) / file).write_text(content, encoding="utf-8")
    with pytest.raises(Exception):
        run(source, "skill", skill="normalize-products", skill_package=package)
    sdk.factory.assert_not_called()


@pytest.mark.parametrize("options", [{"instructions": ""}, {"input": []}, {"input": ["Description", "Description"]},
    {"output": {}}, {"output": {"Name": {"type": "unsupported"}}}, {"timeout": 0}, {"timeout": float("inf")},
    {"model": ""}, {"skill_package": "unused"}])
def test_invalid_configuration_fails_before_runtime(source, sdk, options):
    with pytest.raises(Exception):
        run(source, **options)
    sdk.factory.assert_not_called()


def test_missing_key_and_optional_sdk_are_actionable(source, sdk, monkeypatch):
    with pytest.raises(Exception, match="OPENAI_API_KEY"):
        run(source, api_key=None)
    original_import = builtins.__import__
    def missing_sdk(name, *args, **kwargs):
        if name == "copilot":
            raise ImportError("no sdk")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", missing_sdk)
    with pytest.raises(Exception, match=r"wrangles\[agent\]"):
        run(source)
    sdk.factory.assert_not_called()


def test_empty_dataframe_has_typed_outputs_without_runtime(source, sdk):
    result = run(source.iloc[:0], api_key=None)
    assert result.columns.tolist() == ["Description", "Unrelated", "Name", "Count"]
    assert result.empty
    assert str(result["Count"].dtype) == "int64"
    sdk.factory.assert_not_called()


def test_existing_recipe_never_imports_optional_sdk(source, monkeypatch):
    original_import = builtins.__import__
    def no_sdk(name, *args, **kwargs):
        assert not name.startswith("copilot")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_sdk)
    result = wrangles.recipe.run({"wrangles": [{"rename": {"Description": "Product"}}]}, dataframe=source)
    assert result["Product"].tolist() == source["Description"].tolist()


def test_typed_outputs_can_replace_selected_input(source, sdk):
    sdk.response = {"rows": [{"row_id": i, "Description": name, "Ratio": ratio, "Matched": flag}
        for i, (name, ratio, flag) in enumerate([
            ("Pump Seal", 2.5, True), ("Valve Kit", 1, False), ("Pump Seal", 2.5, True)])]}
    result = run(source, output={"Description": {"type": "string"}, "Ratio": {"type": "number"},
                                 "Matched": {"type": "boolean"}})
    assert result["Description"].tolist() == ["Pump Seal", "Valve Kit", "Pump Seal"]
    assert result["Ratio"].tolist() == [2.5, 1.0, 2.5]
    assert result["Matched"].tolist() == [True, False, True]
    assert result["Unrelated"].tolist() == [7, 8, 9]
    assert source["Description"].tolist() == ["PUMP seal", "valve kit", "pump SEAL"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "2.5"])
def test_invalid_numbers_are_rejected_without_coercion(source, sdk, value):
    sdk.response = {"rows": [{"row_id": i, "Ratio": value} for i in range(3)]}
    with pytest.raises(Exception, match="did not submit"):
        run(source, output={"Ratio": {"type": "number"}})
    assert sdk.submitted.result_type == "failure"


def test_runtime_failure_remains_primary_when_cleanup_also_fails(source, sdk):
    sdk.session.send_and_wait.side_effect = RuntimeError("provider-secret")
    sdk.session.disconnect.side_effect = RuntimeError("disconnect-secret")
    sdk.client.stop.side_effect = RuntimeError("stop-secret")
    sdk.client.force_stop.side_effect = RuntimeError("force-secret")
    with pytest.raises(Exception, match="Local AI runtime failed") as error:
        run(source)
    assert "secret" not in str(error.value)
    sdk.client.force_stop.assert_awaited_once()


def test_environment_key_is_used_without_recipe_credential(source, sdk, monkeypatch, caplog):
    monkeypatch.setenv("OPENAI_API_KEY", "environment-secret")
    result = run(source, api_key=None)
    assert sdk.client.create_session.call_args.kwargs["inference"]["providers"][0]["api_key"] == "environment-secret"
    assert "environment-secret" not in caplog.text
    assert "environment-secret" not in json.dumps(result.attrs)


def test_recipe_schemas_describe_both_entry_points(package):
    import jsonschema
    import yaml
    from wrangles.recipe_wrangles import ai
    options = {"input": ["Description"], "output": OUTPUT, "skill": "normalize-products", "skill_package": package}
    for entry in (ai.agent, ai.skill):
        schema = yaml.safe_load(entry.__doc__)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(options, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"input": "Description", "output": OUTPUT}, yaml.safe_load(ai.agent.__doc__))
    agent_schema = jsonschema.Draft7Validator(yaml.safe_load(ai.agent.__doc__))
    inline = {"input": "Description", "output": OUTPUT, "instructions": "Apply our rules"}
    assert agent_schema.is_valid({**inline, "skills": [{"model_id": "normalize-products"}]})
    assert not agent_schema.is_valid({**inline, "skill_package": package})
    assert not agent_schema.is_valid({**options, "skills": [{"model_id": "second"}]})
