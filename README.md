# backports.asyncio.runner

[![PyPI version][project-badge]](https://pypi.org/project/backports.asyncio.runner)
[![GitHub Actions][github-actions-badge]](https://github.com/samypr100/backports.asyncio.runner/actions/workflows/main.yml)
[![Hatch][hatch-badge]](https://github.com/pypa/hatch)
[![Ruff][ruff-badge]](https://github.com/astral-sh/ruff)
[![Type checked with mypy][mypy-badge]](https://mypy-lang.org)
[![Coverage][coverage-badge]](https://coverage.readthedocs.io)

[project-badge]: https://badge.fury.io/py/backports.asyncio.runner.svg
[github-actions-badge]: https://github.com/samypr100/backports.asyncio.runner/actions/workflows/main.yml/badge.svg
[hatch-badge]: https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg
[ruff-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[mypy-badge]: https://www.mypy-lang.org/static/mypy_badge.svg
[coverage-badge]: https://gist.githubusercontent.com/samypr100/8682bd2df950670a45095c7c109a176e/raw/coverage.svg

This is a backport of Python 3.11 [asyncio.Runner](https://docs.python.org/3/library/asyncio-runner.html#asyncio.Runner), a context manager that simplifies multiple async
function calls in the same context.

This backports provides full compatibility with Python 3.11 `asyncio.Runner` features, including `contextvars.Context` support.
As such, the Python 3.11 test suite for `asyncio.Runner` is used as-is to test its functionality.

This backport is meant to work with Python 3.8, 3.9, and 3.10 only. Users of Python 3.11 or above should
not use this package directly.

To install, you can use `python -m pip install backports.asyncio.runner` or your favorite python package manager.
You might need to include a marker (e.g. `python_version < '3.11'`) to prevent installation on Python 3.11 or above.

An example of the recommended way to use this context manager is in the below code snippet:

```python
import sys

if sys.version_info < (3, 11):
    from backports.asyncio.runner import Runner
else:
    from asyncio import Runner

async def echo(msg: str) -> None:
    print(f"Hello {msg}")

with Runner() as runner:
    runner.run(echo("World"))

# Hello World
```

## uvloop

This backport is also compatible with [uvloop](https://github.com/MagicStack/uvloop). An example is below:

```python
import sys
import uvloop

if sys.version_info < (3, 11):
    from backports.asyncio.runner import Runner
else:
    from asyncio import Runner

async def echo(msg: str) -> None:
    print(f"Hello {msg}")

with Runner(loop_factory=uvloop.new_event_loop) as runner:
    runner.run(echo("World"))

# Hello World
```

## Contributing

Feel free to open a PR if there's changes you'd like to make as long as the changes maintain full reference implementation
with Python 3.11's implementation of `asyncio.Runner`. More documentation and additional tests are always welcome as CPython's
test don't seem to provide 100% coverage at a glance or more likely I may have missed including some tests.

* [ruff](https://github.com/astral-sh/ruff) is used to format the code via `ruff format`.
    * To quickly run ruff, make sure `pipx` is installed an run `pipx run ruff==0.1.8 format src tests`
* [mypy](https://github.com/python/mypy) is used to check types in the sources (while attempting to stay true to reference implementation).
    * To quickly run mypy, make sure `pipx` is installed an run `pipx run mypy==1.7.1 src`
* To run tests use `python -m unittest discover -s tests`.
* To gather coverage:
  * Install coverage: `python -m pip install "coverage[toml]==7.3.3"`
  * Run it: `coverage run -m unittest discover -s tests`

Relevant reference implementation sources:
* https://github.com/python/cpython/blob/3.11/Lib/asyncio/runners.py
* https://github.com/python/cpython/blob/3.11/Lib/asyncio/tasks.py
* https://github.com/python/cpython/blob/3.11/Lib/asyncio/base_events.py
* https://github.com/python/cpython/blob/3.11/Modules/_asynciomodule.c
* https://github.com/python/cpython/blob/3.11/Lib/test/test_asyncio/test_runners.py
* https://github.com/python/cpython/blob/3.8/Lib/test/test_asyncio/test_tasks.py
* https://github.com/python/cpython/blob/3.9/Lib/test/test_asyncio/test_tasks.py
* https://github.com/python/cpython/blob/3.10/Lib/test/test_asyncio/test_tasks.py

## Caveats

This implementation uses `asyncio.tasks._PyTask` instead of `asyncio.tasks._CTask` as it adds additional functionality to
`asyncio.Task` in order to support `asyncio.Runner` requirements. Hence, the `asyncio.Task` implementation `Runner` will
use also comes from this package. As such, problems can arise when checking `isinstance(some_runner_main_task, asyncio.Task)`
since `asyncio.Task` can point to `_CTask` by default instead of `_PyTask`. You may encounter the same issue when comparing
it to `asyncio.Future`.

To guarantee full `asyncio.Task` functionality, upstream tests for `asyncio.Task` for 3.8, 3.9, and 3.10 are also part of the
testing suite of this package to make sure all changes to `asyncio.Task` used by the `Runner` are fully compatible with
`asyncio.Task`. Important Note: `asyncio.Task` is **only** patched on the `Runner`, not globally, hence there should be
no side effects to external code when using this module.

Currently, a backport of `_CTask` is not provided on this package and not in scope at this time. This means that there's a slight
performance degradation when using this `asyncio.Runner` implementation over the one in Python 3.11 or above.
