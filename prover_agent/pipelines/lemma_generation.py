from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from prover_agent._config import TaskConfig
from prover_agent.lean._engine import verify_proof
from prover_agent.pipelines._entry import entry_point
from prover_agent.utils import (
    print_separator,
    print_with_separator,
    remove_import_and_open_and_set_option,
    update_open,
)

if TYPE_CHECKING:
    from prover_agent.pipelines._ctx import LogSession, ProofContext


@dataclass
class LemmaGenerationConfig(TaskConfig):
    num_lemmas: int = field(default=3)


def generate_lemmas(
    ctx: ProofContext,
    log_session: LogSession,
    *,
    max_attempts: int | None = 10,
) -> list[str] | None:
    lemma_generation_cfg: LemmaGenerationConfig = ctx.cfg.lemma_generation
    if max_attempts is None:
        max_attempts = lemma_generation_cfg.max_attempts
    if max_attempts <= 0:
        print("Max attempts reached for lemma generation.")
        return None
    prompt = lemma_generation_cfg.prepare_prompt(
        lean_header=ctx.lean_header,
        theorem=ctx.theorem,
        num_lemmas=lemma_generation_cfg.num_lemmas,
    )
    lemmas_raw = ctx.runner.run(
        lemma_generation_cfg,
        prompt,
        ctx.log_dir,
        log_session.get_log_filename(lemma_generation_cfg.filename),
        resume_from=ctx.resume_from,
    )
    if lemmas_raw:
        lemmas = (
            _format_lemmas(lemmas_raw, lemma_generation_cfg.num_lemmas)
            if not getattr(ctx.cfg, "formalization")
            else formalize_lemmas(ctx, log_session, lemmas_raw=lemmas_raw)
        )
        print("Generated lemmas:")
        print_with_separator(lemmas)
        if lemmas and len(lemmas) == lemma_generation_cfg.num_lemmas:
            return lemmas
    if not max_attempts:
        print("Failed to generate lemmas.")
        return None
    print(
        f"Failed to generate lemmas. Retrying (remaining attempts: {max_attempts})..."
    )
    return generate_lemmas(ctx, log_session, max_attempts=max_attempts - 1)


def _format_lemmas(lemmas: str, max_num_lemmas: int) -> list[str]:
    lemmas = remove_import_and_open_and_set_option(lemmas)
    lemmas_list = lemmas.split("\n\n")
    lemmas_list = [lemma.strip() for lemma in lemmas_list]
    lemmas_list = [
        lemma
        for lemma in lemmas_list
        if any(
            line.startswith("lemma") or line.startswith("theorem")
            for line in lemma.split("\n")
        )
    ]
    return lemmas_list[:max_num_lemmas]


@dataclass
class FormalizationConfig(TaskConfig):
    split_marker: str = field(default="###")
    lemma_format: str = field(default_factory=str)
    extract_name: bool = field(default=False)


def formalize_lemmas(
    ctx: ProofContext,
    log_session: LogSession,
    *,
    lemmas_raw: str,
) -> list[str] | None:
    lemmas = _parse_raw_nl_lemmas(
        lemmas_raw,
        ctx.cfg.formalization.split_marker,
        ctx.cfg.lemma_generation.num_lemmas,
    )
    if not lemmas:
        print("No lemmas found in the raw output.")
        return None
    print(f"Obtained lemmas:\n{lemmas}")
    for lemma in lemmas:
        print(*lemma, sep="\n")
        print_separator()
    formalized_lemmas = [
        _formalize_lemma(ctx, i + 1, *lemma, log_session)
        for i, lemma in enumerate(lemmas)
    ]
    print("Formalized lemmas:")
    print_with_separator(formalized_lemmas)
    return [lemma for lemma in formalized_lemmas if lemma]


def _parse_raw_nl_lemmas(
    lemmas_raw: str,
    split_marker: str,
    num_lemmas: int,
    extract_names: bool = False,
) -> list[tuple[str | None, str]] | None:
    lines = lemmas_raw.splitlines()
    header_indices = [
        i for i, line in enumerate(lines) if line.startswith(split_marker)
    ]
    if len(header_indices) < num_lemmas:
        print("Insufficient lemmas found in the raw output.")
        return None
    lemma_names = [
        re.sub(rf"^{re.escape(split_marker)} \d+: ", "", lines[i])
        .strip()
        .replace("&", "and")
        .replace(" ", "_")
        .lower()
        if extract_names
        else None
        for i in header_indices
    ]
    lemmas = [
        "\n".join(
            line for line in lines[i + extract_names : j] if line.strip() != "---"
        ).strip()
        for i, j in zip(header_indices, header_indices[1:] + [None])
    ]
    lemmas = lemmas[:num_lemmas]
    return list(zip(lemma_names, lemmas))


def _formalize_lemma(
    ctx: ProofContext,
    idx: int,
    lemma_name: str | None,
    lemma_txt: str,
    log_session: LogSession,
    max_attempts: int | None = None,
) -> str | None:
    formalization_cfg: FormalizationConfig = ctx.cfg.formalization
    if max_attempts is None:
        max_attempts = formalization_cfg.max_attempts
    if max_attempts <= 0:
        print(f"Failed to formalize lemma {idx}")
        return None
    prompt = formalization_cfg.prepare_prompt(
        problem_name=lemma_name,
        nl_statement=lemma_txt,
    )
    formalized_lemma = ctx.runner.run(
        formalization_cfg,
        prompt,
        ctx.log_dir,
        log_session.with_suffix(str(idx)).get_log_filename(formalization_cfg.filename),
        resume_from=ctx.resume_from,
    )
    print(f"Formalization result for lemma {idx}:\n{formalized_lemma}")
    print_separator()
    if formalized_lemma:
        header = update_open(ctx.lean_header, formalized_lemma)
        lemma = remove_import_and_open_and_set_option(formalized_lemma)
        lemma = formalization_cfg.lemma_format.format(lemma=lemma, lean_header=header)
        lean_output = verify_proof(
            ctx.workspace,
            lemma,
            allow_sorry=True,
            method=getattr(ctx.cfg, "verifier", None),
        )
        print(f"Lean output for lemma {idx}:\n{lean_output}")
        print_separator()
        if lean_output and lean_output.is_verified():
            return lemma
    print(
        f"Failed to formalize lemma {idx}. Retrying (remaining attempts: {max_attempts})..."
    )
    return _formalize_lemma(
        ctx, idx, lemma_name, lemma_txt, log_session, max_attempts - 1
    )


if __name__ == "__main__":
    entry_point(generate_lemmas)
