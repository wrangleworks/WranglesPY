# Agent Task: Migrate pytest 7.4.4 → 9.0.2

Source: https://github.com/pytest-dev/pytest/releases/tag/8.0.0rc1

## Step 0 — Upgrade and capture baseline

```bash
pip install "pytest>=9.0.2"
pytest --tb=short -q 2>&1 | tee /tmp/pytest_baseline.txt
```

Use the baseline output to verify each fix as you go.

---

## Step 1 — Resolve all PytestRemovedIn8Warning errors

All warnings of type `PytestRemovedIn8Warning` from pytest 7.x are now **hard errors** in pytest 8.

Run the suite and grep for these in the output:

```bash
grep "PytestRemovedIn8Warning" /tmp/pytest_baseline.txt
```

Common causes and fixes:

**a) `pytest.warns(None)` — removed**

```bash
grep -rn "pytest.warns(None)" . --include="*.py"
```

- To assert at least one warning: use `pytest.warns(Warning)`
- To assert no warnings are emitted:
  ```python
  import warnings
  with warnings.catch_warnings():
      warnings.simplefilter("error")
      <code under test>
  ```

**b) `--strict` CLI flag — removed, replaced by `--strict-markers`**

```bash
grep -rn "\-\-strict" . --include="*.ini" --include="*.cfg" \
  --include="*.toml" --include="*.yml" --include="*.yaml" \
  --include="Makefile" --include="*.sh"
```

Replace all occurrences of `--strict` with `--strict-markers`.

**c) `parser.addoption` with string-based types — removed**

```bash
grep -rn 'addoption.*type="' . --include="*.py"
```

```python
# Before
parser.addoption("--count", type="int")
parser.addoption("--name", type="string")

# After
parser.addoption("--count", type=int)
parser.addoption("--name", type=str)
```

**d) `fspath` / `py.path.local` on Node constructors — deprecated, heading to removal**

```bash
grep -rn "py\.path\|fspath" . --include="*.py"
```

```python
# Before
def pytest_collect_file(parent, fspath):
    if fspath.ext == ".yml":
        ...

# After
def pytest_collect_file(parent, file_path):
    if file_path.suffix == ".yml":
        ...
```

---

## Step 2 — Fix `pytest.warns` behavior change

`pytest.warns` now **re-emits unmatched warnings** when the context closes instead of silently consuming them. If your suite is configured with `filterwarnings = error`, any previously-swallowed warnings will now cause failures.

```bash
grep -rn "pytest.warns" . --include="*.py"
```

Check each `pytest.warns` block: if the code under test emits warnings beyond what's being matched, either:
- Add the extra warning type to the `pytest.warns(...)` call
- Or suppress explicitly with `warnings.filterwarnings("ignore", ...)` inside the block

---

## Step 3 — Fix `parser.addini` default value handling

The behavior of `config.getini()` changed when a config option has no value set in the test session:

- If `type` is provided but `default` is not → returns a type-specific default (`False` for bool, `""` for str, etc.)
- If `default=None` is explicitly passed → now correctly returns `None` (previously ignored)
- If neither `type` nor `default` are set → returns `""` (unchanged)

```bash
grep -rn "parser.addini" . --include="*.py"
```

Review each `addini` call. If your plugin code checks the return value of `config.getini()` for truthiness or compares it to `[]` or `""`, verify the new defaults still match your expectations.

---

## Step 4 — Fix collection order sensitivity

Files and directories are now **collected alphabetically together**. Previously, files were collected before directories, which means test execution order may have changed.

To detect if your suite is order-sensitive:

```bash
pytest --collect-only -q 2>&1 | head -50
```

Compare the order to what you had before. If tests are failing due to shared mutable state between tests that ran in a different order:
- Move shared state into fixtures with the appropriate `scope`
- Or use `pytest-ordering` to make order explicit

Also note: running `pytest pkg/__init__.py` now collects **only that file**, not the entire package. If you have CI scripts or Makefiles that do this, update them to `pytest pkg/` to collect the full package.

---

## Step 5 — Fix custom plugins using collection node internals

If you have any custom plugins or `conftest.py` files that interact with pytest's collection tree, the following changed:

**a) `pytest.Package` is no longer a subclass of `pytest.Module` or `pytest.File`**

```bash
grep -rn "pytest.Package\|isinstance.*Package" . --include="*.py"
```

If your plugin does `isinstance(node, pytest.Module)` expecting to match `Package` nodes, this will no longer work. Handle `pytest.Package` separately.

**b) New `pytest.Directory` base class**

Custom directory collectors should now subclass `pytest.Directory` instead of trying to subclass `pytest.File` or other node types.

**c) `session.name` changed**

`session.name` is now `""` (empty string). Previously it was the rootdir directory name. Update any plugin code that reads `session.name` expecting the directory name — use `session.config.rootpath.name` instead.

**d) `pytest.Package` no longer recurses**

`Package` now only collects files in its own directory. Sub-directories are collected by their own nodes. If your plugin relied on `Package.collect()` returning items from sub-directories, it needs to be updated.

---

## Step 6 — Fix marks applied to fixtures (warning in 8.x → error in 9.0)

Applying marks to fixture functions never had any effect, but is now a **warning in 8.x** and will become an **error in 9.0**.

```bash
grep -rn "@pytest.mark" . --include="*.py" | grep -v "def test_"
```

Look for patterns like:

```python
# Wrong — mark on a fixture has no effect
@pytest.mark.usefixtures("db")
@pytest.fixture
def my_fixture():
    ...
```

Remove the mark from the fixture. If you need a fixture to use another fixture, just add it as a parameter:

```python
@pytest.fixture
def my_fixture(db):
    ...
```

---

## Step 7 — Check Python version

pytest 8+ dropped Python 3.7. If your project still supports Python 3.7, you cannot upgrade pytest for that environment. Options:
- Drop Python 3.7 support in the project
- Pin pytest to `<8` for Python 3.7 in your CI matrix and upgrade only for 3.8+

---

## Step 8 — Final verification

Run the full suite:

```bash
pytest --tb=short -q
```

Then run with warnings-as-errors to catch remaining deprecations (which will become errors in pytest 9.x / 10.x):

```bash
pytest -W error::DeprecationWarning -W error::PytestDeprecationWarning --tb=short -q
```

Both should exit with code 0.

---

## Priority Order

| Priority | Issue | Impact |
|----------|-------|--------|
| High | `PytestRemovedIn8Warning` → errors | Will immediately break test runs |
| High | `pytest.warns` re-emitting unmatched warnings | Will break suites with `filterwarnings = error` |
| High | Collection order change | Can cause subtle ordering-dependent failures |
| Medium | `parser.addini` default change | Only affects custom plugins |
| Medium | `pytest.Package` no longer a `Module` | Only affects custom plugins/conftest |
| Medium | Marks on fixtures | Warning now, error in 9.0 |
| Low | `session.name` change | Only affects plugins reading session name |
| Low | Python 3.7 dropped | Only relevant if still supporting 3.7 |
