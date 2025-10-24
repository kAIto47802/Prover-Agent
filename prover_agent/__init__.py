from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from prover_agent._config import TaskConfig, VLLMModelSettings, load_config
from prover_agent.lean import maybe_load_prev_output, verify_proof
from prover_agent.pipelines._ctx import LogSession, ProofContext
from prover_agent.pipelines._entry import EntryFn
from prover_agent.runner import (
    OpenAIApiRunner,
    UnifiedRunner,
    VllmRunner,
)

if TYPE_CHECKING:
    from typing import Any

    from prover_agent.pipelines.integration import (
        integrate_lemmas,
        make_initial_integration,
        make_initial_integration_with_selection,
    )
    from prover_agent.pipelines.lemma_generation import (
        FormalizationConfig,
        LemmaGenerationConfig,
        formalize_lemmas,
        generate_lemmas,
    )
    from prover_agent.pipelines.proof import (
        FixProofConfig,
        InitialProofConfig,
        make_initial_proof,
        make_initial_proof_with_selection,
        make_nl_proof,
        make_proof,
    )
    from prover_agent.pipelines.whole_process import make_proof_with_lemmas


_lazy_map = {
    "integrate_lemmas": "prover_agent.pipelines.integration",
    "make_initial_integration": "prover_agent.pipelines.integration",
    "make_initial_integration_with_selection": "prover_agent.pipelines.integration",
    "FormalizationConfig": "prover_agent.pipelines.lemma_generation",
    "LemmaGenerationConfig": "prover_agent.pipelines.lemma_generation",
    "formalize_lemmas": "prover_agent.pipelines.lemma_generation",
    "generate_lemmas": "prover_agent.pipelines.lemma_generation",
    "FixProofConfig": "prover_agent.pipelines.proof",
    "InitialProofConfig": "prover_agent.pipelines.proof",
    "make_initial_proof": "prover_agent.pipelines.proof",
    "make_initial_proof_with_selection": "prover_agent.pipelines.proof",
    "make_nl_proof": "prover_agent.pipelines.proof",
    "make_proof": "prover_agent.pipelines.proof",
    "make_proof_with_lemmas": "prover_agent.pipelines.whole_process",
}


# Lazy loading of pipeline components to avoid runpy warnings
# See PEP 562 for details: https://www.python.org/dev/peps/pep-0562/
def __getattr__(name: str) -> Any:
    if name in _lazy_map:
        module = importlib.import_module(_lazy_map[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = [
    "TaskConfig",
    "VLLMModelSettings",
    "load_config",
    "maybe_load_prev_output",
    "verify_proof",
    "LogSession",
    "ProofContext",
    "EntryFn",
    "OpenAIApiRunner",
    "UnifiedRunner",
    "VllmRunner",
    "integrate_lemmas",
    "make_initial_integration",
    "make_initial_integration_with_selection",
    "FormalizationConfig",
    "LemmaGenerationConfig",
    "formalize_lemmas",
    "generate_lemmas",
    "FixProofConfig",
    "InitialProofConfig",
    "make_initial_proof",
    "make_initial_proof_with_selection",
    "make_nl_proof",
    "make_proof",
    "make_proof_with_lemmas",
]


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + __all__))


__version__ = "0.1.0"
