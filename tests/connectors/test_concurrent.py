import time

import pandas as pd
import wrangles


# Shared timing values for all concurrent timing tests.
#
# Each task waits for 5 seconds. If the tasks run concurrently, total runtime
# should be roughly 5 seconds plus overhead. If they run serially, total runtime
# should be roughly 15 seconds.
WAIT_SECONDS = 5
TASK_COUNT = 3
SERIAL_RUNTIME_SECONDS = WAIT_SECONDS * TASK_COUNT

# Allow CI overhead, especially on Windows, while still proving the tasks did
# not simply run one after another.
MAX_CONCURRENT_SECONDS = SERIAL_RUNTIME_SECONDS - 2  # 13 seconds


def _assert_concurrent_runtime(elapsed):
    """
    Assert that a set of WAIT_SECONDS tasks ran concurrently rather than serially.
    """
    assert elapsed >= WAIT_SECONDS, (
        f"Expected runtime to be at least {WAIT_SECONDS}s because each task waits "
        f"{WAIT_SECONDS}s, but elapsed time was {elapsed:.2f}s."
    )

    assert elapsed < MAX_CONCURRENT_SECONDS, (
        f"Expected concurrent runtime to be materially less than the "
        f"{SERIAL_RUNTIME_SECONDS}s serial runtime, but elapsed time was "
        f"{elapsed:.2f}s."
    )


def _run_recipe_and_measure(recipe, functions):
    """
    Run a recipe and return both the recipe result and elapsed time.

    time.monotonic() is used for elapsed-time measurement because it is designed
    to move only forward and is not affected by wall-clock changes.
    """
    start = time.monotonic()
    result = wrangles.recipe.run(recipe, functions=functions)
    elapsed = time.monotonic() - start

    return result, elapsed


def wait_and_read(duration):
    time.sleep(duration)
    return pd.DataFrame({"column": [f"value{str(duration)}"]})


def wait_and_append(df, wait, test_vals_key):
    time.sleep(wait)
    test_vals[test_vals_key].append(wait)


def sleep(seconds):
    """
    As a builtin function implemented in C, time.sleep() is not directly
    accessible to the recipe engine. Wrap it as a Python function to make the
    function definition available.
    """
    time.sleep(seconds)


test_vals = {
    "multithread": [],
}



def synchronized_read(directory, task_id, task_count):
    """Require all workers to start before any task may complete."""
    import os
    from pathlib import Path
    import time
    import pandas as pd

    directory = Path(directory)
    (directory / f"{task_id}.ready").touch()
    deadline = time.monotonic() + 30
    while len(list(directory.glob("*.ready"))) < task_count:
        if time.monotonic() >= deadline:
            raise TimeoutError("Concurrent workers did not reach the barrier")
        time.sleep(0.01)
    (directory / f"{task_id}.done").write_text(str(os.getpid()), encoding="ascii")
    return pd.DataFrame({"column": [task_id]})


def _synchronized_actions(directory):
    return [{"custom.synchronized_read": {
        "directory": str(directory), "task_id": i, "task_count": TASK_COUNT,
    }} for i in range(TASK_COUNT)]


def _assert_processes_completed(directory):
    completed = sorted(directory.glob("*.done"))
    assert [path.stem for path in completed] == [str(i) for i in range(TASK_COUNT)]
    assert len({path.read_text(encoding="ascii") for path in completed}) == TASK_COUNT


def test_read_multithread():
    """
    Test using the concurrent connector to read using multiple threads.
    """
    df, elapsed = _run_recipe_and_measure(
        f"""
        read:
          - union:
              sources:
                - concurrent:
                    read:
                    - custom.wait_and_read:
                        duration: {WAIT_SECONDS}
                    - custom.wait_and_read:
                        duration: {WAIT_SECONDS}
                    - custom.wait_and_read:
                        duration: {WAIT_SECONDS}
        """,
        functions=wait_and_read,
    )

    assert len(df) == TASK_COUNT
    _assert_concurrent_runtime(elapsed)


def test_read_multiprocess(tmp_path):
    """Real child processes must overlap, independent of spawn overhead."""
    df = wrangles.recipe.run(
        {"read": [{"union": {"sources": [{"concurrent": {
            "use_multiprocessing": True,
            "max_concurrency": TASK_COUNT,
            "read": _synchronized_actions(tmp_path),
        }}]}}]},
        functions=synchronized_read,
    )

    assert df["column"].tolist() == list(range(TASK_COUNT))
    _assert_processes_completed(tmp_path)


def test_write_multithread():
    """
    Test using the concurrent connector to write using multiple threads.
    """
    test_vals["multithread"] = []

    _, elapsed = _run_recipe_and_measure(
        f"""
        read:
          - test:
              rows: 1
              values:
                header: value
        write:
          - concurrent:
              write:
                - custom.wait_and_append:
                     wait: {WAIT_SECONDS}
                     test_vals_key: multithread
                - custom.wait_and_append:
                     wait: {WAIT_SECONDS}
                     test_vals_key: multithread
                - custom.wait_and_append:
                     wait: {WAIT_SECONDS}
                     test_vals_key: multithread
        """,
        functions=wait_and_append,
    )

    assert test_vals["multithread"] == [WAIT_SECONDS] * TASK_COUNT
    _assert_concurrent_runtime(elapsed)


def test_run_multithread():
    """
    Test using the concurrent connector to run using multiple threads.
    """
    _, elapsed = _run_recipe_and_measure(
        f"""
        run:
          on_start:
          - concurrent:
              run:
                - custom.sleep:
                     seconds: {WAIT_SECONDS}
                - custom.sleep:
                     seconds: {WAIT_SECONDS}
                - custom.sleep:
                     seconds: {WAIT_SECONDS}
        """,
        functions=sleep,
    )

    _assert_concurrent_runtime(elapsed)


def test_run_multiprocess(tmp_path):
    """Every action completes in a distinct, overlapping child process."""
    wrangles.recipe.run(
        {"run": {"on_start": [{"concurrent": {
            "use_multiprocessing": True,
            "max_concurrency": TASK_COUNT,
            "run": _synchronized_actions(tmp_path),
        }}]}},
        functions=synchronized_read,
    )

    _assert_processes_completed(tmp_path)
