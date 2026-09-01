"""
Registry of model IDs referenced by the WranglesPY test suite.

scripts/check_model_registry_access.py checks access to every model
listed here before the credentialed test suite runs, so a missing or
inaccessible model fails fast with a clear report instead of causing
a cascade of individual test failures deep into the run.

This file was seeded by scanning tests/**/test_*.py for real-looking
model IDs (8-4-4 hex, excluding obvious placeholders like
00000000-0000-0000). It needs human review: remove any ID that is
only ever used against a mocked wrangles.data.model/model_content -
those never hit the network and don't belong in an access-precheck.
"""

MODEL_REGISTRY = {
    "05f6bb73-de04-4cb6": "tests/recipes/wrangles/test_extract.py",
    "083ed6fe-a073-4b1a": "tests/connectors/test_train.py",
    "0e81f1ad-c0a3-42b4": "tests/recipes/wrangles/test_extract.py (+1 more files)",
    "12b7ac66-7418-45b5": "tests/connectors/test_train.py",
    "1ac1dddb-fcb5-45f3": "tests/recipes/wrangles/test_main.py",
    "1b41d016-7129-4b66": "tests/recipes/test_recipes.py",
    "1e13e845-bc3f-4b27": "tests/connectors/test_recipe.py (+2 more files)",
    "1eddb7e8-1b2b-4a52": "tests/recipes/wrangles/test_extract.py (+1 more files)",
    "1f3ba62b-ce20-486e": "tests/recipes/wrangles/test_extract.py",
    "3c8f6707-2de4-4be3": "tests/connectors/test_train.py",
    "41789e35-eada-4239": "tests/connectors/test_train.py",
    "4202c974-430a-46b9": "tests/connectors/test_train.py",
    "42f319a8-0849-4177": "tests/connectors/test_recipe.py (+1 more files)",
    "5313d577-0bb6-4174": "tests/connectors/test_train.py",
    "6ca4ab44-8c66-40e8": "tests/recipes/wrangles/test_extract.py (+2 more files)",
    "6e97bb6c-bfab-402b": "tests/recipes/wrangles/test_main.py",
    "73d89595-e5c9-40a4": "tests/recipes/wrangles/test_extract.py",
    "829c1a73-1bfd-4ac0": "tests/recipes/wrangles/test_extract.py",
    "89637e77-7214-49a0": "tests/connectors/test_train.py",
    "8dd00032-d8bb-400c": "tests/recipes/wrangles/test_extract.py",
    "8e4ce4c6-9908-4f67": "tests/recipes/wrangles/test_extract.py",
    # NOTE: 93d92b4c-9f49-4ff5 (tests/test_data.py) intentionally omitted -
    # confirmed mocked-only (FakeResponse harness, never hits the network).
    "94674750-f9e1-44af": "tests/connectors/test_train.py",
    "a62c7480-500e-480c": "tests/recipes/test_recipes.py (+2 more files)",
    "b2cd1a8a-4d99-4be1": "tests/connectors/test_train.py",
    # NOTE: bc3ee6a0-e104-4700 (tests/connectors/test_train.py) intentionally
    # omitted - confirmed mocked-only (test_missing_columns_error_message
    # mocks wrangles.data.model/model_content directly).
    "c37af8a6-43d8-4127": "tests/recipes/test_recipes.py",
    "c3e6715a-6214-4517": "tests/recipes/wrangles/test_extract.py",
    "d168c456-514f-4513": "tests/recipes/wrangles/test_extract.py",
    "d188e7a7-9de8-4565": "tests/connectors/test_train.py",
    "d7c8270d-f15a-4c9c": "tests/recipes/wrangles/test_extract.py",
    "e8658a6f-c694-45d0": "tests/connectors/test_train.py (+2 more files)",
    "e954717c-fb9c-4c47": "tests/recipes/test_recipes.py",
    "ee320e2b-ccda-47ed": "tests/connectors/test_train.py",
    "ee5f020e-d88e-4bd5": "tests/connectors/test_train.py",
    "fc7d46e3-057f-47bd": "tests/connectors/test_http.py (+2 more files)",
    "fce592c9-26f5-4fd7": "tests/recipes/test_recipes.py (+1 more files)",
    "fe730444-1bda-4fcd": "tests/recipes/wrangles/test_main.py (+1 more files)",
    # NOTE: fe885889-67f2-4f3a (tests/recipes/test_recipes.py) intentionally
    # omitted - not a model_id at all. It's the first three groups of the
    # longer version_id fe885889-67f2-4f3a-b33a-1a37ff5c243c, used as
    # "c37af8a6-43d8-4127:fe885889-67f2-4f3a-b33a-1a37ff5c243c" in
    # test_recipe_by_version_id. The extraction regex (8-4-4 hex) matched
    # inside it by accident - confirmed by the checker correctly reporting
    # it as inaccessible on its first live CI run.
}

