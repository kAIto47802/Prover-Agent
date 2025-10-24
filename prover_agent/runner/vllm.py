from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from prover_agent._config import VLLMModelSettings
from prover_agent.runner._base import BaseRunner
from prover_agent.runner._register import register_runner

if TYPE_CHECKING:
    from transformers import PreTrainedTokenizer, PreTrainedTokenizerFast
    from vllm import LLM

    from prover_agent._config import TaskConfig


@dataclass
class _ModelAndTokenizer:
    model: LLM
    tokenizer: PreTrainedTokenizer | PreTrainedTokenizerFast | None = None


@register_runner("vllm")
class VllmRunner(BaseRunner):
    def __init__(self) -> None:
        self._models: dict[str, _ModelAndTokenizer] = {}

    def _prepare_lazy(
        self,
        task_cfg: TaskConfig,
    ) -> None:
        from transformers import AutoTokenizer
        from vllm import LLM

        assert isinstance(task_cfg.model, VLLMModelSettings)
        if (model_name := task_cfg.model.model) not in self._models:
            model = LLM(
                seed=42,
                trust_remote_code=True,
                **{k: v for k, v in asdict(task_cfg.model).items() if v is not None},
            )
            self._models[model_name] = _ModelAndTokenizer(model)
        if task_cfg.messages and self._models[model_name].tokenizer is None:
            self._models[model_name].tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True,
            )

    def _generate_output(
        self,
        task_cfg: TaskConfig,
        prompt: str,
    ) -> str | None:
        assert isinstance(task_cfg.model, VLLMModelSettings)
        model_name = task_cfg.model.model
        if task_cfg.messages:
            tokenizer = self._models[model_name].tokenizer
            assert tokenizer is not None
            prompt = tokenizer.apply_chat_template(
                task_cfg.messages(prompt),
                tokenize=False,
                add_generation_prompt=True,
            )  # type: ignore
        output = self._models[model_name].model.generate(
            prompt,
            sampling_params=task_cfg.sampling_params,
            use_tqdm=False,
        )
        return output[0].outputs[0].text
