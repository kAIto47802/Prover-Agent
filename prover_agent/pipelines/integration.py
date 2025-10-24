from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from prover_agent.lean._engine import maybe_load_prev_output, verify_proof
from prover_agent.pipelines._entry import entry_point
from prover_agent.pipelines.proof import fix_proof_loop
from prover_agent.utils import (
    convert_to_lemma,
    print_separator,
    remove_import_and_open_and_set_option,
    restore_theorem_statements,
)

if TYPE_CHECKING:
    from prover_agent.pipelines._ctx import LogSession, ProofContext
    from prover_agent.pipelines.proof import InitialProofConfig


def make_initial_integration(
    ctx: ProofContext,
    log_session: LogSession,
    lemmas: list[str],
) -> str | None:
    integration_cfg: InitialProofConfig = ctx.cfg.integration
    theorem = integration_cfg.prepare_theorem(ctx.theorem)
    prompt = integration_cfg.prepare_prompt(
        theorem=theorem,
        lemmas="\n\n".join(lemmas),
        lean_header=ctx.lean_header,
    )
    required_contents = integration_cfg.prepare_required_contents(
        theorem=theorem,
        lemmas="\n\n".join(lemmas),
        lean_header=ctx.lean_header,
    )
    output_prefix = integration_cfg.prepare_output_prefix(
        lemmas="\n\n".join(lemmas),
        lean_header=ctx.lean_header,
    )
    res = ctx.runner.run(
        integration_cfg,
        prompt,
        ctx.log_dir,
        log_file := log_session.with_prefix("i_").get_log_filename(
            integration_cfg.filename
        ),
        resume_from=ctx.resume_from,
        required_contents=required_contents,
        post_process_fns=[
            remove_import_and_open_and_set_option,
            lambda t: restore_theorem_statements(t, theorem),
        ],
        output_prefix=output_prefix,
    )
    if res:
        ctx.results[log_file.as_posix()] = res
    return res


def make_initial_integration_with_selection(
    ctx: ProofContext,
    log_session: LogSession,
    *,
    lemmas: list[str],
    depth: int = 0,
) -> str | None:
    proof = None
    lean_output = None
    num_errors_min = 1 << 30
    num_selections = (
        ns if isinstance(ns := ctx.cfg.integration.num_selections, int) else ns[depth]
    )
    for i in range(num_selections):
        print(f"Selection {i + 1} of {num_selections}")
        cur_log_session = log_session.with_suffix(f"_{i + 1}")
        cur_proof = make_initial_integration(ctx, cur_log_session, lemmas)

        if not cur_proof:
            print(f"Initial integration generation failed for selection {i + 1}.")
            continue

        cur_lean_output = maybe_load_prev_output(
            ctx.resume_from,
            output_file := cur_log_session.get_log_filename(
                ctx.cfg.integration.filename
            ).with_suffix(".out"),
            cur_proof,
            method=getattr(ctx.cfg, "verifier", None),  # type: ignore
        ) or verify_proof(
            ctx.workspace,
            cur_proof,
            method=getattr(ctx.cfg, "verifier", None),
        )

        if not cur_lean_output:
            print(f"Could not get Lean4 output for selection {i + 1}.")
            continue
        (output_path := (Path(ctx.log_dir) / output_file)).parent.mkdir(
            parents=True, exist_ok=True
        )
        cur_lean_output.save(output_path)
        print("Lean4 Output:")
        print(cur_lean_output)

        if cur_lean_output.is_verified():
            print("Integration verified!")
            return cur_proof
        if (num_errors := cur_lean_output.num_errors) < num_errors_min:
            num_errors_min = num_errors
            proof = cur_proof
            lean_output = cur_lean_output
    if proof is None:
        print("No valid proof found after all selections.")
        return None
    cur_log_session = log_session.with_suffix("_best")
    proof_file = cur_log_session.get_log_filename(ctx.cfg.integration.filename)
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


def _retrieve_lemmas(
    ctx: ProofContext,
    log_session: LogSession,
) -> list[str]:
    lemmas = []
    assert ctx.resume_from, "No resume_from path provided for lemma retrieval."
    for lemma_dir in Path(ctx.resume_from).iterdir():
        if not lemma_dir.is_dir() or "lemma" not in lemma_dir.name:
            continue
        files = list(lemma_dir.glob("*.lean"))
        files = (
            [file for file in files if file.name.startswith("i_")]
            or [file for file in files if file.name.startswith("fix_")]
            or [file for file in files if file.name.startswith("Main")]
        )
        file = max(files, key=lambda x: int(x.stem.split("_")[-1]))
        print(f"Retrieving {file} from {lemma_dir}")
        cur_lean_output = maybe_load_prev_output(
            ctx.resume_from,
            log_session.get_log_filename(ctx.cfg.initial_proof.filename).with_suffix(
                ".out"
            ),
            proof := file.read_text(),
            method=getattr(ctx.cfg, "verifier", None),  # type: ignore
        ) or verify_proof(
            ctx.workspace,
            proof,
            method=getattr(ctx.cfg, "verifier", None),
        )
        if cur_lean_output and cur_lean_output.is_verified():
            print(f"Lemma verified from {file}.")
            lemmas.append(proof)
    print(lemmas)
    lemmas = [remove_import_and_open_and_set_option(lemma) for lemma in lemmas]
    lemmas = [convert_to_lemma(lemma) for lemma in lemmas]
    return lemmas


def integrate_lemmas(
    ctx: ProofContext,
    log_session: LogSession,
    *,
    lemmas: list[str] | None = None,
    depth: int = 0,
) -> str | None:
    print("Integrating lemmas with lemmas:")
    lemmas = (
        lemmas or getattr(ctx.cfg, "lemmas", None) or _retrieve_lemmas(ctx, log_session)
    )
    for lemma in lemmas:
        print(lemma)
    print_separator()
    return make_initial_integration_with_selection(
        ctx,
        log_session.with_prefix("i_"),
        lemmas=lemmas,
        depth=depth,
    ) or fix_proof_loop(
        ctx,
        ctx.cfg.fix_integration,
        log_session.with_prefix("i_"),
        depth=depth,
        lemmas=lemmas,
    )


if __name__ == "__main__":
    entry_point(integrate_lemmas)
