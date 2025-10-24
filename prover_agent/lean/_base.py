from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import sys
    from pathlib import Path
    from typing import Any

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


@dataclass
class ErrorInfo:
    line: int
    code: str
    message: str


class LeanOutputBase(ABC):
    def __init__(self, raw: Any, code: str, allow_sorry: bool = False) -> None:
        self._raw = raw
        self._code = code
        self._allow_sorry = allow_sorry

    @property
    @abstractmethod
    def _error_messages(self) -> list[Any]:
        pass

    def is_verified(self) -> bool:
        return not self._error_messages

    @property
    def num_errors(self) -> int:
        return len(self._error_messages)

    @abstractmethod
    def errors(self, max_error_lines: int | None = None) -> list[ErrorInfo]:
        pass

    @classmethod
    @abstractmethod
    def load_if_exists(
        cls, path: Path | str, code: str, allow_sorry: bool = False
    ) -> Self | None:
        pass

    @abstractmethod
    def save(self, path: Path | str) -> None:
        pass

    def __str__(self) -> str:
        return str(self._raw)


class VerifyProofProtocol(Protocol):
    def __call__(
        self,
        workspace: Path | str,
        code: str,
        max_attempts: int = 20,
        allow_sorry: bool = False,
    ) -> LeanOutputBase | None: ...
