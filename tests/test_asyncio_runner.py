import _thread
import asyncio
import contextvars
import re
import signal
import threading
import unittest
from asyncio import AbstractEventLoop, Future, Task
from typing import Callable, Optional
from unittest import mock
from unittest.mock import patch

import backports.asyncio.runner.runner
from backports.asyncio.runner import Runner


# See https://github.com/python/cpython/blob/3.11/Lib/test/test_asyncio/test_runners.py


def tearDownModule() -> None:
    asyncio.set_event_loop_policy(None)


def interrupt_self() -> None:
    _thread.interrupt_main()


class TestPolicy(asyncio.AbstractEventLoopPolicy):
    def __init__(self, loop_factory: Callable[[], AbstractEventLoop]):
        self.loop_factory = loop_factory
        self.loop = None

    def get_event_loop(self) -> None:  # type: ignore[override]
        # shouldn't ever be called by asyncio.run()
        raise RuntimeError

    def new_event_loop(self) -> AbstractEventLoop:
        return self.loop_factory()

    def set_event_loop(self, loop: Optional[AbstractEventLoop]) -> None:
        if loop is not None:
            # we want to check if the loop is closed
            # in BaseTest.tearDown
            self.loop = loop  # type: ignore[assignment]


class BaseTest(unittest.TestCase):
    def new_loop(self) -> AbstractEventLoop:
        loop = asyncio.BaseEventLoop()
        loop._process_events = mock.Mock()  # type: ignore[attr-defined]
        # Mock waking event loop from select
        loop._write_to_self = mock.Mock()  # type: ignore[attr-defined]
        loop._write_to_self.return_value = None  # type: ignore[attr-defined]
        loop._selector = mock.Mock()  # type: ignore[attr-defined]
        loop._selector.select.return_value = ()  # type: ignore[attr-defined]
        loop.shutdown_ag_run = False  # type: ignore[attr-defined]

        async def shutdown_asyncgens() -> None:
            loop.shutdown_ag_run = True  # type: ignore[attr-defined]

        loop.shutdown_asyncgens = shutdown_asyncgens  # type: ignore[method-assign]

        return loop

    def setUp(self) -> None:
        super().setUp()

        policy = TestPolicy(self.new_loop)  # type: ignore[abstract]
        asyncio.set_event_loop_policy(policy)

    def tearDown(self) -> None:
        policy = asyncio.get_event_loop_policy()
        if policy.loop is not None:  # type: ignore[attr-defined]
            self.assertTrue(policy.loop.is_closed())  # type: ignore[attr-defined]
            self.assertTrue(policy.loop.shutdown_ag_run)  # type: ignore[attr-defined]

        asyncio.set_event_loop_policy(None)
        super().tearDown()


class RunnerTests(BaseTest):
    def test_non_debug(self) -> None:
        with Runner(debug=False) as runner:
            self.assertFalse(runner.get_loop().get_debug())

    def test_debug(self) -> None:
        with Runner(debug=True) as runner:
            self.assertTrue(runner.get_loop().get_debug())

    def test_custom_factory(self) -> None:
        loop = mock.Mock()
        # Note: This would cause a warning since a mock can't run_until_complete our implementation of _shutdown_default_executor in 3.8
        with patch.object(
            backports.asyncio.runner.runner, "_shutdown_default_executor", mock.Mock()
        ):
            with Runner(loop_factory=lambda: loop) as runner:
                self.assertIs(runner.get_loop(), loop)

    def test_run(self) -> None:
        async def f() -> str:
            await asyncio.sleep(0)
            return "done"

        with Runner() as runner:
            self.assertEqual("done", runner.run(f()))
            loop = runner.get_loop()

        with self.assertRaisesRegex(RuntimeError, "Runner is closed"):
            runner.get_loop()

        self.assertTrue(loop.is_closed())

    def test_run_non_coro(self) -> None:
        with Runner() as runner:
            with self.assertRaisesRegex(ValueError, "a coroutine was expected"):
                runner.run(123)  # type: ignore[arg-type]

    def test_run_future(self) -> None:
        with Runner() as runner:
            with self.assertRaisesRegex(ValueError, "a coroutine was expected"):
                fut = runner.get_loop().create_future()
                runner.run(fut)  # type: ignore[arg-type]

    def test_explicit_close(self) -> None:
        runner = Runner()
        loop = runner.get_loop()
        runner.close()
        with self.assertRaisesRegex(RuntimeError, "Runner is closed"):
            runner.get_loop()

        self.assertTrue(loop.is_closed())

    def test_double_close(self) -> None:
        runner = Runner()
        loop = runner.get_loop()

        runner.close()
        self.assertTrue(loop.is_closed())

        # the second call is no-op
        runner.close()
        self.assertTrue(loop.is_closed())

    def test_second_with_block_raises(self) -> None:
        ret = []

        async def f(arg: int) -> None:
            ret.append(arg)

        runner = Runner()
        with runner:
            runner.run(f(1))

        with self.assertRaisesRegex(RuntimeError, "Runner is closed"):
            with runner:
                runner.run(f(2))

        self.assertEqual([1], ret)

    def test_run_keeps_context(self) -> None:
        cvar = contextvars.ContextVar("cvar", default=-1)

        async def f(val: int) -> int:
            old = cvar.get()
            await asyncio.sleep(0)
            cvar.set(val)
            return old

        async def get_context() -> contextvars.Context:
            return contextvars.copy_context()

        with Runner() as runner:
            self.assertEqual(-1, runner.run(f(1)))
            self.assertEqual(1, runner.run(f(2)))

            self.assertEqual(2, runner.run(get_context()).get(cvar))

    def test_recursive_run(self) -> None:
        async def g() -> None:
            pass

        async def f() -> None:
            runner.run(g())

        with Runner() as runner:
            with self.assertWarnsRegex(
                RuntimeWarning,
                "coroutine .+ was never awaited",
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    re.escape(
                        "Runner.run() cannot be called from a running event loop"
                    ),
                ):
                    runner.run(f())

    def test_interrupt_call_soon(self) -> None:
        # The only case when task is not suspended by waiting a future
        # or another task
        assert threading.current_thread() is threading.main_thread()

        async def coro() -> None:
            with self.assertRaises(asyncio.CancelledError):
                while True:
                    await asyncio.sleep(0)
            raise asyncio.CancelledError()

        with Runner() as runner:
            runner.get_loop().call_later(0.1, interrupt_self)
            with self.assertRaises(KeyboardInterrupt):
                runner.run(coro())

    def test_interrupt_wait(self) -> None:
        # interrupting when waiting a future cancels both future and main task
        assert threading.current_thread() is threading.main_thread()

        async def coro(fut: Future) -> None:
            with self.assertRaises(asyncio.CancelledError):
                await fut
            raise asyncio.CancelledError()

        with Runner() as runner:
            fut = runner.get_loop().create_future()
            runner.get_loop().call_later(0.1, interrupt_self)

            with self.assertRaises(KeyboardInterrupt):
                runner.run(coro(fut))

            self.assertTrue(fut.cancelled())

    def test_interrupt_cancelled_task(self) -> None:
        # interrupting cancelled main task doesn't raise KeyboardInterrupt
        assert threading.current_thread() is threading.main_thread()

        async def subtask(task: Task) -> None:
            await asyncio.sleep(0)
            task.cancel()
            interrupt_self()

        async def coro() -> None:
            asyncio.create_task(subtask(asyncio.current_task()))  # type: ignore[arg-type]
            await asyncio.sleep(10)

        with Runner() as runner:
            with self.assertRaises(asyncio.CancelledError):
                runner.run(coro())

    def test_signal_install_not_supported_ok(self) -> None:
        # signal.signal() can throw if the "main thread" doesn't have signals enabled
        assert threading.current_thread() is threading.main_thread()

        async def coro() -> None:
            pass

        with Runner() as runner:
            with patch.object(
                signal,
                "signal",
                side_effect=ValueError(
                    "signal only works in main thread of the main interpreter"
                ),
            ):
                runner.run(coro())

    def test_set_event_loop_called_once(self) -> None:
        # See https://github.com/python/cpython/issues/95736
        async def coro() -> None:
            pass

        policy = asyncio.get_event_loop_policy()
        policy.set_event_loop = mock.Mock()  # type: ignore[method-assign]
        runner = Runner()
        runner.run(coro())
        runner.run(coro())

        self.assertEqual(1, policy.set_event_loop.call_count)
        runner.close()

    def test_no_repr_is_call_on_the_task_result(self) -> None:
        # See https://github.com/python/cpython/issues/112559
        class MyResult:
            def __init__(self) -> None:
                self.repr_count = 0

            def __repr__(self) -> str:
                self.repr_count += 1
                return super().__repr__()

        async def coro() -> MyResult:
            return MyResult()

        with Runner() as runner:
            result = runner.run(coro())

        self.assertEqual(0, result.repr_count)


if __name__ == "__main__":
    unittest.main()
