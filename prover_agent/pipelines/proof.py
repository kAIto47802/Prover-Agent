from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from prover_agent._config import TaskConfig
from prover_agent.lean._engine import maybe_load_prev_output, verify_proof
from prover_agent.pipelines._entry import entry_point
from prover_agent.utils import (
    print_separator,
    remove_import_and_open_and_set_option,
    restore_theorem_statements,
)

if TYPE_CHECKING:
    from prover_agent.lean._base import LeanOutputBase
    from prover_agent.pipelines._ctx import LogSession, ProofContext


def make_nl_proof(
    ctx: ProofContext,
    log_session: LogSession,
) -> str | None:
    nl_proof_cfg: TaskConfig = ctx.cfg.nl_proof
    theorem = nl_proof_cfg.prepare_theorem(ctx.theorem)
    prompt = nl_proof_cfg.prepare_prompt(
        theorem=theorem,
        lean_header=ctx.lean_header,
    )
    res = ctx.runner.run(
        nl_proof_cfg,
        prompt,
        ctx.log_dir,
        log_file=(log_file := log_session.get_log_filename(nl_proof_cfg.filename)),
        resume_from=ctx.resume_from,
    )
    if res:
        ctx.results[log_file.as_posix()] = res
    return res


@dataclass
class InitialProofConfig(TaskConfig):
    num_selections: int | list[int] = field(default=100)


def make_initial_proof(
    ctx: ProofContext,
    log_session: LogSession,
) -> str | None:
    initial_proof_cfg: InitialProofConfig = ctx.cfg.initial_proof
    theorem = initial_proof_cfg.prepare_theorem(ctx.theorem)
    prompt = initial_proof_cfg.prepare_prompt(
        nl_proof=ctx.cfg.nl_proof
        and ctx.results[
            log_session.get_log_filename(ctx.cfg.nl_proof.filename).as_posix()
        ],
        theorem=theorem,
        lean_header=ctx.lean_header,
    )
    required_contents = initial_proof_cfg.prepare_required_contents(
        theorem=theorem,
        lean_header=ctx.lean_header,
    )
    output_prefix = initial_proof_cfg.prepare_output_prefix(
        lean_header=ctx.lean_header,
    )
    res = ctx.runner.run(
        initial_proof_cfg,
        prompt,
        ctx.log_dir,
        log_file := log_session.get_log_filename(initial_proof_cfg.filename),
        required_contents=required_contents,
        resume_from=ctx.resume_from,
        post_process_fns=[
            remove_import_and_open_and_set_option,
            lambda t: restore_theorem_statements(t, theorem),
        ],
        output_prefix=output_prefix,
    )
    if res:
        ctx.results[log_file.as_posix()] = res
    return res


def make_initial_proof_with_selection(
    ctx: ProofContext,
    log_session: LogSession,
    *,
    depth: int = 0,
) -> str | None:
    nl_proof = None
    proof = None
    lean_output = None
    num_errors_min = 1 << 30
    num_selections = (
        ns if isinstance(ns := ctx.cfg.initial_proof.num_selections, int) else ns[depth]
    )
    for i in range(num_selections):
        print(f"Selection {i + 1} of {num_selections}")
        cur_log_session = log_session.with_suffix(f"_{i + 1}")

        cur_nl_proof = ctx.cfg.nl_proof and make_nl_proof(ctx, cur_log_session)
        cur_proof = make_initial_proof(ctx, cur_log_session)

        if not cur_proof:
            print(f"Initial proof generation failed for selection {i + 1}.")
            continue

        cur_lean_output = maybe_load_prev_output(
            ctx.resume_from,
            output_file := cur_log_session.get_log_filename(
                ctx.cfg.initial_proof.filename
            ).with_suffix(".out"),
            cur_proof,
            method=getattr(ctx.cfg, "verifier", None),  # type: ignore
        ) or verify_proof(
            ctx.workspace,
            cur_proof,
            method=getattr(ctx.cfg, "verifier", None),
        )

        if cur_lean_output is None:
            print(f"Could not get Lean4 output for selection {i + 1}.")
            continue
        (output_path := (Path(ctx.log_dir) / output_file)).parent.mkdir(
            parents=True, exist_ok=True
        )
        cur_lean_output.save(output_path)
        print("Lean4 Output:")
        print(cur_lean_output)

        if cur_lean_output.is_verified():
            print("Proof verified!")
            return cur_proof

        if (num_errors := cur_lean_output.num_errors) < num_errors_min:
            num_errors_min = num_errors
            nl_proof = cur_nl_proof
            proof = cur_proof
            lean_output = cur_lean_output
    if proof is None:
        print("No valid proof found after all selections.")
        return None
    best_log_session = log_session.with_suffix("_best")
    if nl_proof:
        nl_proof_file = best_log_session.get_log_filename(ctx.cfg.nl_proof.filename)
        (Path(ctx.log_dir) / nl_proof_file).write_text(nl_proof)
        ctx.results[nl_proof_file.as_posix()] = nl_proof
    proof_file = best_log_session.get_log_filename(ctx.cfg.initial_proof.filename)
    (Path(ctx.log_dir) / proof_file).write_text(proof)
    ctx.results[proof_file.as_posix()] = proof
    assert lean_output is not None
    lean_output.save(
        Path(ctx.log_dir) / (output_file := proof_file.with_suffix(".out"))
    )
    ctx.results[output_file.as_posix()] = lean_output
    print(f"Proof could not be verified after {num_selections} selections.")
    print(f"The least number of errors: {num_errors_min}.")
    return None


@dataclass
class FixProofConfig(TaskConfig):
    error_line_message: str = field(default_factory=str)
    max_fix_attempts: int | list[int] = field(default=100)
    max_fix_prompt_lines: int | None = field(default=500)
    max_error_lines: int | None = field(default=30)


def _fix_proof(
    ctx: ProofContext,
    fix_proof_cfg: FixProofConfig,
    prev_nl_proof: str | None,
    prev_code: str,
    prev_lean_output: LeanOutputBase,
    log_session: LogSession,
    *,
    lemmas: list[str] | None = None,
) -> str | None:
    error_line_messages = [
        fix_proof_cfg.error_line_message.format(
            error_line=output.line,
            error_code=output.code,
            error_message=output.message,
        )
        for output in prev_lean_output.errors(fix_proof_cfg.max_error_lines)
    ]
    if fix_proof_cfg.max_fix_prompt_lines:
        num_error_lines = [len(t.splitlines()) for t in error_line_messages]
        index = np.searchsorted(
            np.cumsum(num_error_lines), fix_proof_cfg.max_fix_prompt_lines, "right"
        )
        error_line_messages = error_line_messages[:index]
    print_separator()
    theorem = fix_proof_cfg.prepare_theorem(ctx.theorem)
    prompt = fix_proof_cfg.prepare_prompt(
        theorem=theorem,
        lean_header=ctx.lean_header,
        nl_proof=prev_nl_proof,
        prev_code=prev_code,
        error_line_messages="\n\n".join(error_line_messages),
        lemmas="\n\n".join(lemmas) if lemmas else "",
    )
    required_contents = fix_proof_cfg.prepare_required_contents(
        theorem=theorem,
        lemmas="\n\n".join(lemmas) if lemmas else "",
        lean_header=ctx.lean_header,
    )
    output_prefix = fix_proof_cfg.prepare_output_prefix(
        lean_header=ctx.lean_header,
        lemmas="\n\n".join(lemmas) if lemmas else "",
    )
    return ctx.runner.run(
        fix_proof_cfg,
        prompt,
        ctx.log_dir,
        log_session.get_log_filename(fix_proof_cfg.filename),
        required_contents=required_contents,
        resume_from=ctx.resume_from,
        post_process_fns=[
            remove_import_and_open_and_set_option,
            lambda t: restore_theorem_statements(t, theorem),
        ],
        output_prefix=output_prefix,
    )


def fix_proof_loop(
    ctx: ProofContext,
    fix_proof_cfg: FixProofConfig,
    log_session: LogSession,
    *,
    depth: int = 0,
    lemmas: list[str] | None = None,
) -> str | None:
    if getattr(ctx.cfg, "stop_after_initial_proof", False):
        raise RuntimeError("Stopping after initial proof generation.")
    best_log_session = log_session.with_suffix("_best")
    print(list(ctx.results.keys()))
    prev_nl_proof = ctx.cfg.nl_proof and ctx.results.get(
        best_log_session.get_log_filename(ctx.cfg.nl_proof.filename).as_posix()
    )
    best_file = best_log_session.get_log_filename(ctx.cfg.initial_proof.filename)
    prev_code = ctx.results[best_file.as_posix()]
    prev_lean_output: LeanOutputBase = ctx.results[
        best_file.with_suffix(".out").as_posix()
    ]
    revised_code: str | None = None
    max_fix_attempts = (
        fa if isinstance(fa := fix_proof_cfg.max_fix_attempts, int) else fa[depth]
    )
    for i in range(max_fix_attempts):
        print(f"Fixing proof (attempt {i + 1})...")
        cur_log_session = log_session.with_suffix(f"_{i + 1}")
        revised_code = _fix_proof(
            ctx,
            fix_proof_cfg,
            prev_nl_proof,
            prev_code,
            prev_lean_output,
            cur_log_session,
            lemmas=lemmas,
        )
        if not revised_code:
            print(f"Proof fixing failed at attempt {i + 1}.")
            continue
        cur_lean_output = maybe_load_prev_output(
            ctx.resume_from,
            output_file := cur_log_session.get_log_filename(
                fix_proof_cfg.filename
            ).with_suffix(".out"),
            revised_code,
            method=getattr(ctx.cfg, "verifier", None),
        ) or verify_proof(
            ctx.workspace,
            revised_code,
            method=getattr(ctx.cfg, "verifier", None),
        )
        if cur_lean_output is None:
            print("Could not get Lean4 output.")
            continue
        (output_path := (Path(ctx.log_dir) / output_file)).parent.mkdir(
            parents=True, exist_ok=True
        )
        cur_lean_output.save(output_path)
        print("Lean4 Output:")
        print(cur_lean_output)
        if cur_lean_output.is_verified():
            print("Proof verified!")
            return revised_code
        prev_code = revised_code
        prev_lean_output = cur_lean_output
    print(f"Proof could not be fixed after {max_fix_attempts} attempts.")

    return None


def make_proof(
    ctx: ProofContext,
    log_session: LogSession,
    *,
    depth: int = 0,
) -> str | None:
    return make_initial_proof_with_selection(
        ctx,
        log_session,
        depth=depth,
    ) or fix_proof_loop(
        ctx,
        ctx.cfg.fix_proof,
        log_session,
        depth=depth,
    )


if __name__ == "__main__":
    entry_point(make_proof)
