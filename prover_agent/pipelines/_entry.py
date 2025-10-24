from __future__ import annotations

import argparse
import traceback
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Concatenate, ParamSpec

from prover_agent._config import load_config
from prover_agent.pipelines._ctx import LogSession, ProofContext
from prover_agent.runner.unified import UnifiedRunner
from prover_agent.utils import (
    make_model_url_mapping,
)

if TYPE_CHECKING:
    pass


P = ParamSpec("P")


EntryFn = Callable[Concatenate[ProofContext, LogSession, P], str | list[str] | None]


def entry_point(entry_fn: EntryFn) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="final")
    parser.add_argument("--lean_workspace", type=str, default="lean_workspace")
    parser.add_argument(
        "--additional_name",
        type=str,
        help="Additional identifier used only for naming the log directory",
    )
    parser.add_argument("--timestamp", type=str, required=False)
    parser.add_argument(
        "--model_url_mapping",
        nargs="*",
        type=str,
        help=(
            "Mapping between model names and their corresponding URLs. "
            "Specify pairs as: <model_name> <url>. For example:\n\n"
            f"  python -m prover_agent.pipelines.{entry_fn.__name__} \\\n"
            "    --model_url_mapping \\\n"
            "      deepseek-ai/DeepSeek-R1-0528-Qwen3-8B http://<your-endpoint-1>/v1 \\\n"
            "      Goedel-LM/Goedel-Prover-V2-8B http://<your-endpoint-2>/v1"
        ),
    )
    parser.add_argument("--resume_from", type=str, help="Log directory to resume from")
    args = parser.parse_args()

    cfg = load_config(args.config, args.additional_name)

    runner = UnifiedRunner(
        model_url_mapping=args.model_url_mapping
        and make_model_url_mapping(args.model_url_mapping)
    )

    timestamp = args.timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")  # type: ignore

    log_dir = Path(f"runs/run-{cfg.config_name}-{timestamp}")
    log_dir.mkdir(parents=True, exist_ok=True)

    ctx = ProofContext(
        cfg,
        cfg.theorem,
        log_dir,
        args.lean_workspace,
        runner,
        args.resume_from and Path(f"runs/{args.resume_from}"),
    )
    log_session = LogSession()

    with open(log_dir / "logs.txt", "w") as log_file:
        with redirect_stdout(log_file), redirect_stderr(log_file):
            try:
                entry_fn(ctx, log_session)
            except Exception:
                traceback.print_exc()
