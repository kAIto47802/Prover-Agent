from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from multiprocessing import Manager
from pathlib import Path
from typing import TYPE_CHECKING, cast

from prover_agent import (
    LogSession,
    ProofContext,
    UnifiedRunner,
    generate_lemmas,
    integrate_lemmas,
    load_config,
    make_proof,
    make_proof_with_lemmas,
)
from prover_agent.utils import make_model_url_mapping

if TYPE_CHECKING:
    from multiprocessing.managers import DictProxy, ValueProxy
    from threading import Lock

    from prover_agent import EntryFn


def worker(
    args: argparse.Namespace,
    theorem_id: int,
    theorem: str,
    resume_from: str | None,
    counter: ValueProxy[int],
    pid_dict: DictProxy[int, int],
    lock: Lock,
) -> None:
    process_id = os.getpid()
    with lock:
        if process_id not in pid_dict:
            pid_dict[process_id] = counter.value
        counter.value += 1
        worker_id = pid_dict[process_id]

    print("+=" * 40)
    print(f"[{theorem_id}] (worker: {worker_id})")
    print(theorem)
    print("-" * 80)

    if args.num_gpus_per_worker:
        os.environ["CUDA_VISIBLE_DEVICES"] = ",".join(
            [
                str(worker_id * args.num_gpus_per_worker + i)
                for i in range(args.num_gpus_per_worker)
            ]
        )

    cfg = load_config(args.config, args.additional_name)

    runner = UnifiedRunner(
        model_url_mapping=args.model_url_mapping
        and make_model_url_mapping(args.model_url_mapping)
    )

    log_dir = Path(
        f"runs/{args.benchmark}_{args.phase}_{cfg.config_name}_{args.timestamp}/theorem{theorem_id}"
    )
    log_dir.mkdir(parents=True, exist_ok=True)

    ctx = ProofContext(
        cfg,
        theorem,
        log_dir,
        args.lean_workspace,
        runner,
        resume_from and Path(f"runs/{resume_from}/theorem{theorem_id}"),
    )
    log_session = LogSession()

    with open(log_dir / "logs.txt", "w") as log_file:
        with redirect_stdout(log_file), redirect_stderr(log_file):
            try:
                registry: dict[str, EntryFn] = {
                    "make_proof": make_proof,
                    "generate_lemmas": generate_lemmas,
                    "integrate_lemmas": integrate_lemmas,
                    "make_proof_with_lemmas": make_proof_with_lemmas,
                }
                registry[args.dispatch_fn](ctx, log_session)
            except Exception:
                traceback.print_exc()


def _make_resume_map(
    resume_map_raw: list[str],
    num_theorems: int,
) -> list[str | None]:
    resume_map: list[str | None] = [None] * num_theorems
    if not resume_map_raw:
        return resume_map
    assert len(resume_map_raw) % 2 == 0, (
        "Resume map must have an even number of elements."
    )
    for i in range(0, len(resume_map_raw), 2):
        resume_map[int(resume_map_raw[i])] = resume_map_raw[i + 1]
    for i in range(1, len(resume_map)):
        if not resume_map[i]:
            resume_map[i] = resume_map[i - 1]
    return resume_map


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="final")
    parser.add_argument("--lean_workspace", type=str, default="lean_workspace")
    parser.add_argument("--dispatch_fn", type=str, default="make_proof_with_lemmas")
    parser.add_argument(
        "--additional_name",
        type=str,
        help="Additional identifier used only for naming the log directory",
    )
    parser.add_argument("--timestamp", type=str, required=False)
    parser.add_argument("--benchmark", type=str, default="miniF2F")
    parser.add_argument("--phase", type=str, default="test")
    parser.add_argument("--num_workers", type=int, default=8)
    parser.add_argument("--num_gpus_per_worker", type=int)
    parser.add_argument("--range_min", type=int, help="Minimum theorem index to run")
    parser.add_argument("--range_max", type=int, help="Maximum theorem index to run")
    parser.add_argument(
        "--theorems", nargs="*", type=int, help="Specific theorem indices to run"
    )
    parser.add_argument(
        "--exclude_theorems", nargs="*", type=int, help="Theorem indices to exclude"
    )
    parser.add_argument(
        "--resume_map",
        nargs="*",
        type=str,
        help=(
            "Mapping of theorem indices to log directories for resuming runs. "
            "Specify pairs as: <theorem_index> <log_directory>. For example:\n\n"
            "  python dispatch_benchmark.py \\\n"
            "    --resume_map \\\n"
            "      0 miniF2F_test_final_20251010-101010 \\\n"
            "      12 miniF2F_test_final_20251010-111111\n\n"
            "Indices not specified will inherit the previous one."
        ),
    )
    parser.add_argument(
        "--model_url_mapping",
        nargs="*",
        type=str,
        help=(
            "Mapping between model names and their corresponding URLs. "
            "Specify pairs as: <model_name> <url>. For example:\n\n"
            "  python dispatch_benchmark.py \\\n"
            "    --model_url_mapping \\\n"
            "      deepseek-ai/DeepSeek-R1-0528-Qwen3-8B http://<your-endpoint-1>/v1 \\\n"
            "      Goedel-LM/Goedel-Prover-V2-8B http://<your-endpoint-2>/v1"
        ),
    )
    args = parser.parse_args()

    args.timestamp = args.timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")

    with open(Path("data") / args.benchmark / f"{args.phase}.json") as f:
        theorems = json.load(f)
    theorem_ids = cast(list[int], args.theorems) or list(
        range(args.range_min or 0, args.range_max or len(theorems))
    )
    if args.exclude_theorems:
        theorem_ids = [i for i in theorem_ids if i not in args.exclude_theorems]

    resume_map = _make_resume_map(args.resume_map, len(theorems))

    with Manager() as manager:
        counter = manager.Value("i", 0)
        pid_dict = manager.dict()
        lock = manager.Lock()

        with concurrent.futures.ProcessPoolExecutor(
            max_workers=args.num_workers
        ) as executor:
            futures = {
                executor.submit(
                    worker, args, i, theorems[i], resume_map[i], counter, pid_dict, lock
                ): i
                for i in theorem_ids
            }
            for future in concurrent.futures.as_completed(futures):
                future.result()
