from __future__ import annotations

from typing import TYPE_CHECKING

from openai import APITimeoutError, OpenAI

from prover_agent.runner._base import BaseRunner
from prover_agent.runner._register import register_runner

if TYPE_CHECKING:
    from prover_agent._config import TaskConfig


@register_runner("openai_api")
class OpenAIApiRunner(BaseRunner):
    def __init__(self, model_url_mapping: dict[str, str] | None = None) -> None:
        self._model_url_mapping = model_url_mapping
        self._clients: dict[str, OpenAI] = {}

    def _prepare_lazy(
        self,
        task_cfg: TaskConfig,
    ) -> None:
        assert isinstance(task_cfg.model, str)
        if task_cfg.model not in self._clients:
            self._clients[task_cfg.model] = OpenAI(
                base_url=self._model_url_mapping[task_cfg.model]
                if self._model_url_mapping
                else "http://0.0.0.0:4000",  # litellm default
                api_key="tok",
            )

    def _generate_output(
        self,
        task_cfg: TaskConfig,
        prompt: str,
    ) -> str | None:
        assert isinstance(task_cfg.model, str)
        assert task_cfg.messages is not None, (
            "messages must be provided for VLLM server"
        )
        try:
            completion = self._clients[task_cfg.model].chat.completions.create(
                model=task_cfg.model,
                messages=task_cfg.messages(prompt),  # type: ignore
                max_tokens=task_cfg.max_tokens,
            )
            return completion.choices[0].message.content
        except APITimeoutError as e:
            print(f"API call timed out: {e}. Retrying...")
            return None
