from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from prover_agent.runner._base import BaseRunner

_RUNNER_REGISTRY: dict[str, type[BaseRunner]] = {}


def register_runner(name: str) -> Callable[[type[BaseRunner]], type[BaseRunner]]:
    def decorator(cls: type[BaseRunner]) -> type[BaseRunner]:
        _RUNNER_REGISTRY[name] = cls
        return cls

    return decorator


def get_runner(name: str) -> type[BaseRunner]:
    if name not in _RUNNER_REGISTRY:
        raise ValueError(f"Runner '{name}' is not registered.")
    return _RUNNER_REGISTRY[name]
