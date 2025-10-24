from __future__ import annotations

from typing import TYPE_CHECKING

from prover_agent.utils import extract_first_comment, remove_preceding_comments

if TYPE_CHECKING:
    from typing import Any

    from prover_agent._config import TaskConfig


def prepare_prompt(
    task_cfg: TaskConfig,
    **kwargs: Any,
) -> str:
    return task_cfg.prompt.format(**kwargs)


def prepare_required_contents(
    task_cfg: TaskConfig,
    **kwargs: Any,
) -> list[str] | None:
    required_contents = task_cfg.required_contents and [
        template.format(
            **kwargs,
        )
        for template in task_cfg.required_contents
    ]
    return required_contents


def prepare_output_prefix(
    task_cfg: TaskConfig,
    **kwargs: Any,
) -> str | None:
    return task_cfg.output_prefix and task_cfg.output_prefix.format(**kwargs)


def prepare_theorem(
    task_cfg: TaskConfig,
    theorem: str,
) -> str:
    return {
        "comment": extract_first_comment,
        "code": remove_preceding_comments,
        "comment_and_code": lambda x: x,
    }[task_cfg.code_comment_type](theorem) or ""
