from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, Literal, TypeAlias

from prover_agent._prompts import (
    prepare_output_prefix,
    prepare_prompt,
    prepare_required_contents,
    prepare_theorem,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from vllm import SamplingParams

# NOTE: Python 3.12 introduces the type statement, so once Python 3.11 is dropped,
# it should be updated to use that instead.
Config: TypeAlias = SimpleNamespace | ModuleType
CodeCommentType: TypeAlias = Literal["comment", "code", "comment_and_code"]


@dataclass
class VLLMModelSettings:
    model: str
    max_num_batched_tokens: int | None = None
    gpu_memory_utilization: float = 0.9
    max_model_len: int | None = None
    max_num_seqs: int | None = None
    tensor_parallel_size: int | None = None
    enable_chunked_prefill: bool = True


@dataclass
class TaskConfig:
    model: str | VLLMModelSettings
    filename: str
    prompt: str
    initial_content: str = field(default_factory=str)
    runner_type: str = field(default="openai_api")
    sampling_params: SamplingParams | None = field(default=None)  # for vllm_local
    max_tokens: int | None = field(default=None)  # for vllm_server
    required_contents: list[str] | None = field(default=None)
    messages: Callable[[str], list[dict[str, str]]] | None = field(default=None)
    extract_output_format: Literal["code", "text", "all"] = field(default="code")
    output_start_marker: str | None = field(default=None)
    max_attempts: int = field(default=3)
    output_prefix: str | None = field(default=None)
    forbidden_strings: list[str] | None = field(default=None)
    code_comment_type: CodeCommentType = field(default="comment_and_code")

    def prepare_theorem(self, theorem: str) -> str:
        return prepare_theorem(self, theorem)

    def prepare_prompt(self, **kwargs: Any) -> str:
        return prepare_prompt(self, **kwargs)

    def prepare_required_contents(self, **kwargs: Any) -> list[str] | None:
        return prepare_required_contents(self, **kwargs)

    def prepare_output_prefix(self, **kwargs: Any) -> str | None:
        return prepare_output_prefix(self, **kwargs)


def load_config(config_name: str, additional_name: str | None = None) -> Config:
    cfg = importlib.import_module(f"configs.{config_name}")
    cfg.config_name = config_name + (additional_name or "")  # type: ignore
    return cfg
