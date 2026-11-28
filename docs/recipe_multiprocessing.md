# Recipe multiprocessing and worker counts

Use threads when a recipe spends most of its time waiting for files, databases,
or remote APIs. Threads can overlap those waits. Try `use_multiprocessing: true`
when independent batches spend most of their time running Python code locally,
such as comparing product descriptions against a list of candidate labels.
On a standard CPython build, separate worker processes can run that code on
different CPU cores.

Processes take time to start and must copy data between the parent and workers.
Small tasks and wide DataFrames can cost more to transfer than to process.
Many numeric NumPy operations already release Python's global interpreter lock
and can run in parallel with threads. Compare elapsed time and peak memory on
the same representative input before choosing a mode. [NumPy threading guidance](https://numpy.org/doc/stable/reference/thread_safety.html)

## Set the worker count

Set the worker limit on the operation that divides the work. It is the maximum
number of batches, branches, or variable combinations that can run at once.
Each operation defaults to `use_multiprocessing: false`.

| Recipe operation | One worker handles | Worker-count option | Default |
| --- | --- | --- | ---: |
| `batch` wrangle | One batch of rows at a time | `threads` | 1 |
| `concurrent` wrangle | One independent wrangle with declared output columns | `max_concurrency` | 10 |
| `concurrent` connector in `read`, `write`, or `run` | One listed action | `max_concurrency` | 10 |
| `matrix` connector in `read`, `write`, or `run` | One set of variable values | `max_concurrency` | 10 |

**In `batch`, `threads` counts workers in both modes.** Turning on multiprocessing
with the default count creates one child process. `batch_size` controls rows per
batch and defaults to 1,000. The separate `matrix` **wrangle** applies its steps
sequentially to the DataFrame. [Worker-count naming follow-up](https://github.com/wrangleworks/WranglesPY/issues/1298#worker-count-naming-follow-up)

For CPU-bound work, start with a worker count at or below the number of CPU
cores available to the job. Allow enough batches or branches to keep the
workers busy. For remote I/O, choose a limit the service can sustain.

## Run a CPU-heavy batch in processes

Save this recipe as `score.wrgl.yml`. With 20,000 input rows it creates four
batches of 5,000 rows, runs up to four worker processes, and joins their
results in batch order.

```yaml
wrangles:
  - batch:
      batch_size: 5000
      threads: 4
      use_multiprocessing: true
      wrangles:
        - custom.closest_label:
            output: Matched Label
```

Save this script beside the recipe and run it with Python. The custom function's
`description` argument takes its value from the column of the same name.

```python
from difflib import get_close_matches
from pathlib import Path

import pandas as pd
import wrangles

RECIPE = Path(__file__).with_name("score.wrgl.yml")
LABELS = ("ball bearing", "roller bearing", "bearing housing")


def closest_label(description):
    return get_close_matches(description, LABELS, n=1, cutoff=0.0)[0]


if __name__ == "__main__":
    products = pd.DataFrame({"description": ["ball bearng", "bearing housng"] * 10_000})
    result = wrangles.recipe.run(RECIPE, dataframe=products, functions=closest_label)
    print(result["Matched Label"].head(2).tolist())
```

The first two labels are `ball bearing` and `bearing housing`. Define custom
worker functions at module scope so workers can import them. The `__main__`
guard lets the parent start the recipe once while each child imports the function.
Wrangles uses the configured `spawn` or `forkserver` start method. When the
configured or platform default is `fork`, Wrangles uses `forkserver` where
available and falls back to `spawn`.

Pass the data workers need through recipe inputs or variables and return results
through the operation's outputs. Python must be able to pickle these values to
send them between processes. Each process has its own Python globals and
Wrangles `memory` connector. With the `concurrent` wrangle, each branch receives
a copy of the entire input DataFrame. Give independent branches distinct output
columns.

## Limit concurrent reads with threads

With `east.csv` and `west.csv` in the working directory, this recipe reads both
files and combines their rows. Omitting `use_multiprocessing` selects threads.

```yaml
read:
  - union:
      sources:
        - concurrent:
            max_concurrency: 2
            read:
              - file: {name: east.csv}
              - file: {name: west.csv}
```

The WranglesPY runtime accepts `use_multiprocessing` on the operations listed
above. The recipe schemas for the `batch` and `concurrent` wrangles omit the flag,
so schema-based editors can flag it as an unknown property.
