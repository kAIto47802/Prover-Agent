from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from prover_agent.pipelines._entry import entry_point
from prover_agent.pipelines.integration import integrate_lemmas
from prover_agent.pipelines.lemma_generation import generate_lemmas
from prover_agent.pipelines.proof import make_proof
from prover_agent.utils import (
    convert_to_lemma,
    convert_to_theorem,
    get_theorem_name,
    print_separator,
    print_with_separator,
    remove_import_and_open_and_set_option,
    set_theorem_name,
    split_comments,
    update_open,
)

if TYPE_CHECKING:
    from prover_agent.pipelines._ctx import LogSession, ProofContext


def make_proof_with_lemmas(
    ctx: ProofContext,
    log_session: LogSession,
    *,
    depth: int = 0,
) -> str | None:
    if not getattr(ctx.cfg, "skip_direct_proof", False) and (
        res := make_proof(ctx, log_session, depth=depth)
    ):
        print(f"Proof verified at depth {depth} without lemmas.")
        return res
    print_separator()
    if depth == ctx.cfg.max_depth:
        print(f"Max depth reached for theorem: {ctx.theorem}")
        return None

    lemmas = generate_lemmas(ctx, log_session) or []
    print_separator()

    lemmas = [convert_to_theorem(lemma) for lemma in lemmas]
    lemma_comments, lemmas = map(
        list, zip(*[split_comments(lemma) for lemma in lemmas])
    )
    lemmas = [_remove_sorry_and_initial_proof(lemma) for lemma in lemmas]
    print("Prepared lemmas:\n")
    print_with_separator(lemmas)
    print_separator()

    proved_lemmas = [
        proved_lemma
        for i, lemma in enumerate(lemmas)
        if (
            proved_lemma := make_proof_with_lemmas(
                ctx.with_new_theorem(lemma),
                log_session.with_sub_dir(f"lemma{i}"),
                depth=depth + 1,
            )
        )
    ]

    print_separator()
    print("Proved lemmas:\n")
    print_with_separator(proved_lemmas)
    print_separator()
    for lemma in proved_lemmas:
        ctx.lean_header = update_open(ctx.lean_header, lemma)
    proved_lemmas = [convert_to_lemma(lemma) for lemma in proved_lemmas]
    proved_lemmas = _gather_comments(lemma_comments, proved_lemmas)
    proved_lemmas = [
        remove_import_and_open_and_set_option(lemma) for lemma in proved_lemmas
    ]
    proved_lemmas = _convert_dupulicated_lemma_name(ctx.theorem, proved_lemmas)

    print("Final lemmas:\n")
    for lemma in proved_lemmas:
        print(lemma)
    print_separator()

    return integrate_lemmas(ctx, log_session, lemmas=proved_lemmas, depth=depth)


def _gather_comments(lemma_comments: list[str], lemmas: list[str]) -> list[str]:
    return [comment + "\n" + lemma for comment, lemma in zip(lemma_comments, lemmas)]


def _remove_sorry_and_initial_proof(lemma: str) -> str:
    return lemma.split(":= by")[0] + ":= by\n"


def _convert_dupulicated_lemma_name(theorem: str, lemmas: list[str]) -> list[str]:
    theorem_name = get_theorem_name(theorem)
    lemma_names = [get_theorem_name(lemma) for lemma in lemmas]
    counts = Counter(lemma_names)
    lemma_names = [
        f"lemma{i}" if counts[name] > 1 or name == theorem_name else name
        for i, name in enumerate(lemma_names)
    ]
    return [set_theorem_name(lemma, name) for lemma, name in zip(lemmas, lemma_names)]


if __name__ == "__main__":
    entry_point(make_proof_with_lemmas)
