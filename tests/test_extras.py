"""Extra tests to cover additional functionality in support of upstream tests."""

import _thread
import asyncio
import concurrent.futures
import unittest
from asyncio import futures, Task
from concurrent.futures import ThreadPoolExecutor, Future, ProcessPoolExecutor
from typing import Coroutine, Any, TypeVar, Callable, Set
from unittest.mock import patch

from backports.asyncio.runner import Runner
from backports.asyncio.runner.runner import _cancel_all_tasks  # type: ignore[attr-defined]
from backports.asyncio.runner.runner import _shutdown_default_executor  # type: ignore[attr-defined]

T = TypeVar("T")


async def basic_coro() -> str:
    return "ham"


async def delayed_coro() -> str:
    await asyncio.sleep(0.5)
    return "ham"


async def interrupting_coro() -> str:
    await asyncio.sleep(0.25)
    _thread.interrupt_main()
    return "ham"


async def unreachable_result_coro() -> str:
    strong_ref: Set[Task] = set()
    task = asyncio.create_task(interrupting_coro())
    task.add_done_callback(strong_ref.discard)
    return await delayed_coro()


async def runner_patched_coro(runner: Runner) -> None:
    runner._interrupt_count = 1  # type: ignore[attr-defined]
    await unreachable_result_coro()


def sync_func() -> str:
    return "ham"


def raising_func(*_: Any, **__: Any) -> str:
    raise RuntimeError("ham")


def invoke_runner(coro: Callable[..., Coroutine[Any, Any, T]]) -> T:
    with Runner() as runner:
        return runner.run(coro())


class MissingCoverageTests(unittest.TestCase):
    def test_no_threading(self) -> None:
        result = invoke_runner(basic_coro)

        self.assertEqual(result, "ham")

    def test_with_threading(self) -> None:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut: Future[str] = pool.submit(invoke_runner, basic_coro)
            result = fut.result()
        self.assertEqual(result, "ham")

    def test_with_threading_and_delayed_task(self) -> None:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut: Future[str] = pool.submit(invoke_runner, delayed_coro)
            with self.assertRaises(concurrent.futures.TimeoutError):
                fut.result(timeout=0.1)

    def test_with_process(self) -> None:
        with ProcessPoolExecutor(max_workers=1) as pool:
            fut: Future[str] = pool.submit(invoke_runner, basic_coro)
            result = fut.result()
        self.assertEqual(result, "ham")

    def test_with_process_and_delayed_task(self) -> None:
        with ProcessPoolExecutor(max_workers=1) as pool:
            fut: Future[str] = pool.submit(invoke_runner, delayed_coro)
            with self.assertRaises(concurrent.futures.TimeoutError):
                fut.result(timeout=0.1)

    def test_interrupted(self) -> None:
        with self.assertRaises(KeyboardInterrupt):
            invoke_runner(unreachable_result_coro)

    def test_interrupted_not_done(self) -> None:
        with Runner() as runner:
            with self.assertRaises(KeyboardInterrupt):
                runner.run(runner_patched_coro(runner))

    def test_tasks_cancellation(self) -> None:
        loop = asyncio.new_event_loop()

        # Create two pending _PyTask
        with patch.object(asyncio.tasks, "Task", asyncio.tasks._PyTask):  # type: ignore[attr-defined]
            _ = loop.create_task(basic_coro())
            task_2 = loop.create_task(basic_coro())
            # Simulate second task cannot be cancelled - ignores .cancel()
            task_2.cancel = lambda: False  # type: ignore[method-assign]
        # Simulate an exception on the second task.
        futures._PyFuture.set_exception(task_2, RuntimeError("ham"))  # type: ignore[attr-defined]
        # Change second task back to pending otherwise .cancelled() will return true.
        task_2._state = futures._PENDING  # type: ignore[attr-defined]

        _cancel_all_tasks(loop)

    def test_executor_shutdown(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        future = loop.run_in_executor(None, sync_func)
        result = loop.run_until_complete(future)
        self.assertEqual(result, "ham")
        # Make sure _shutdown_default_executor raises
        old_ref = loop._default_executor.shutdown  # type: ignore[attr-defined]
        loop._default_executor.shutdown = raising_func  # type: ignore[attr-defined]

        with self.assertRaises(RuntimeError):
            loop.run_until_complete(_shutdown_default_executor(loop))

        loop._default_executor.shutdown = old_ref  # type: ignore[attr-defined]
        loop.close()

        asyncio.set_event_loop(None)


if __name__ == "__main__":
    unittest.main()
