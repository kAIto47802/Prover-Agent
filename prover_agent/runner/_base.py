from __future__ import annotations

import shutil
from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING

from prover_agent.utils import print_separator

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Literal

    from prover_agent._config import TaskConfig


class BaseRunner(ABC):
    def run(
        self,
        task_cfg: TaskConfig,
        prompt: str,
        log_dir: Path | str,
        log_file: Path | str,
        *,
        required_contents: list[str] | None = None,
        resume_from: Path | str | None = None,
        post_process_fns: list[Callable[[str], str]]
        | Callable[[str], str]
        | None = None,
        output_format: str | None = None,
        output_prefix: str | None = None,
    ) -> str | None:
        (log_file_path := (Path(log_dir) / log_file)).parent.mkdir(
            parents=True, exist_ok=True
        )
        if resume_from and (resume_file := (Path(resume_from) / log_file)).exists():
            print(f"Resuming from {resume_file}")
            shutil.copy(resume_file, log_file_path)
            return resume_file.read_text()
        print("Running task with configuration:")
        print(f"| log_dir: {log_dir}")
        print(f"| log_filename: {log_file}")
        return self._run_impl(
            task_cfg,
            prompt,
            log_file_path,
            required_contents,
            post_process_fns,
            output_format,
            output_prefix,
        )

    def _run_impl(
        self,
        task_cfg: TaskConfig,
        prompt: str,
        log_file_path: Path | str,
        required_contents: list[str] | None = None,
        post_process_fns: list[Callable[[str], str]]
        | Callable[[str], str]
        | None = None,
        output_format: str | None = None,
        output_prefix: str | None = None,
    ) -> str | None:
        # User can also customize the whole running process by overriding this method.
        self._prepare_lazy(task_cfg)
        for i in range(task_cfg.max_attempts):
            print_separator()
            print(prompt)
            print_separator()
            output_raw = self._generate_output(task_cfg, prompt)
            print_separator()
            print(output_raw)
            print_separator()
            output = output_raw and _extract_output(
                output_raw,
                task_cfg.extract_output_format,
                task_cfg.output_start_marker,
            )
            if not output:
                print("Output is empty.")
                print(
                    f"Failed to capture output. Retrying ({i + 1}/{task_cfg.max_attempts})..."
                )
                continue
            print_separator()
            print("Captured output:")
            print(output)
            if post_process_fns:
                print_separator()
                print("Applying post-processing function...")
                for post_process_fn in (
                    post_process_fns
                    if isinstance(post_process_fns, list)
                    else [post_process_fns]
                ):
                    print(f"Apply {post_process_fn.__name__}")
                    output = post_process_fn(output)
                    print(output)
                    print_separator()
                print("Post-processed output:")
                print(output)
            print_separator()
            if output_format:
                output = output_format.format(output=output)
                print("Formatted output:")
                print(output)
                print_separator()
            if output_prefix:
                output = output_prefix + output
                print("Prefixed output:")
                print(output)
                print_separator()
            if task_cfg.forbidden_strings and any(
                fs in output for fs in task_cfg.forbidden_strings
            ):
                print("Output contains forbidden strings.")
                print(
                    f"Failed to capture output. Retrying ({i + 1}/{task_cfg.max_attempts})..."
                )
                continue
            if all(text in output for text in (required_contents or [])):
                Path(log_file_path).write_text(output)
                return output
            print_separator()
            for text in required_contents or []:
                if text not in output:
                    print(f"Output does not contain required text:\n{text}")
            print(
                f"Failed to capture output. Retrying ({i + 1}/{task_cfg.max_attempts})..."
            )
        print("Failed to generate output")
        return None

    def _prepare_lazy(self, task_cfg: TaskConfig) -> None:
        pass

    def _generate_output(self, task_cfg: TaskConfig, prompt: str) -> str | None:
        pass


def _extract_output(
    output: str,
    format: Literal["code", "text", "all"],
    output_start_marker: str | None = None,
) -> str | None:
    if output_start_marker:
        if output_start_marker not in output:
            print(f"`{output_start_marker}` not found in output.")
            return None
        output = output.split(output_start_marker)[-1].strip()
    return {
        "code": _extract_code,
        "text": _extract_text,
        "all": lambda x: x,
    }[format](output)


def _extract_code(output: str) -> str | None:
    lines = output.split("\n")
    indices = [i for i, line in enumerate(lines) if "```" in line]
    if len(indices) < 2:
        print("No code block found in output.")
        return None
    start_idx = indices[-2]
    end_idx = indices[-1]
    num_indent = len(lines[start_idx].split("```")[0])
    target_lines = lines[start_idx + 1 : end_idx]
    target_lines = [line[num_indent:] for line in target_lines]
    return "\n".join(target_lines)


def _extract_text(output: str) -> str:
    return output.split("```")[0].strip()
