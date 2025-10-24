from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from prover_agent.lean.lake import LakeOutput
from prover_agent.lean.lake import verify_proof as verify_proof_lake
from prover_agent.lean.pantograph import PantographOutput
from prover_agent.lean.pantograph import verify_proof as verify_proof_pantograph
from prover_agent.lean.repl import ReplOutput
from prover_agent.lean.repl import verify_proof as verify_proof_repl

if TYPE_CHECKING:
    from prover_agent.lean._base import LeanOutputBase, VerifyProofProtocol

VerifierType = Literal["pantograph", "repl", "lake"]


def verify_proof(
    workspace: Path | str,
    code: str,
    max_attempts: int = 5,
    *,
    allow_sorry: bool = False,
    method: VerifierType | None = None,
) -> LeanOutputBase | None:
    registry: dict[VerifierType, VerifyProofProtocol] = {
        "pantograph": verify_proof_pantograph,
        "repl": verify_proof_repl,
        "lake": verify_proof_lake,
    }
    return registry[method or "lake"](workspace, code, max_attempts, allow_sorry)


def maybe_load_prev_output(
    resume_from: Path | str | None,
    log_file: str | Path,
    code: str,
    *,
    allow_sorry: bool = False,
    method: VerifierType | None = None,
) -> LeanOutputBase | None:
    registry: dict[VerifierType, type[LeanOutputBase]] = {
        "pantograph": PantographOutput,
        "repl": ReplOutput,
        "lake": LakeOutput,
    }
    return (
        registry[method or "lake"].load_if_exists(
            Path(resume_from) / log_file, code, allow_sorry
        )
        if resume_from
        else None
    )
