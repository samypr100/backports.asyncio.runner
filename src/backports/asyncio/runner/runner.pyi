from _typeshed import Unused
from asyncio import AbstractEventLoop
from collections.abc import Callable, Coroutine
from contextvars import Context
from typing import Any, TypeVar
from typing_extensions import Self, final

__all__ = ("Runner",)

_T = TypeVar("_T")

@final
class Runner:
    def __init__(
        self,
        *,
        debug: bool | None = None,
        loop_factory: Callable[[], AbstractEventLoop] | None = None,
    ) -> None: ...
    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type: Unused, exc_val: Unused, exc_tb: Unused) -> None: ...
    def close(self) -> None: ...
    def get_loop(self) -> AbstractEventLoop: ...
    def run(
        self, coro: Coroutine[Any, Any, _T], *, context: Context | None = None
    ) -> _T: ...
