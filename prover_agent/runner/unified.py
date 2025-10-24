from __future__ import annotations

from typing import TYPE_CHECKING

from prover_agent.runner._base import BaseRunner
from prover_agent.runner._register import get_runner

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any

    from prover_agent._config import TaskConfig


class UnifiedRunner(BaseRunner):
    def __init__(self, **kwargs: Any) -> None:
        self._kwargs = kwargs
        self._runners: dict[str, BaseRunner] = {}

    def _run_impl(
        self,
        task_cfg: TaskConfig,
        prompt: str,
        log_file_path: Path | str,
        required_contents: list[str] | None = None,
        post_process_fns: list[Callable[[str], str]]
        | Callable[[str], str]
        | None = None,
        output_format: str | None = None,
        output_prefix: str | None = None,
    ) -> str | None:
        if (runner_type := task_cfg.runner_type) not in self._runners:
            self._runners[runner_type] = get_runner(runner_type)(**self._kwargs)
        return self._runners[runner_type]._run_impl(
            task_cfg,
            prompt,
            log_file_path,
            required_contents,
            post_process_fns,
            output_format,
            output_prefix,
        )
