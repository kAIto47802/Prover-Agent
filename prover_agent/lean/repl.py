from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from prover_agent.lean._base import ErrorInfo, LeanOutputBase
from prover_agent.utils import print_separator

if TYPE_CHECKING:
    import sys
    from typing import Any

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


class ReplOutput(LeanOutputBase):
    def __init__(
        self, raw: dict[str, Any], code: str, allow_sorry: bool = False
    ) -> None:
        super().__init__(raw, code, allow_sorry)

    @property
    def _error_messages(self) -> list[Any]:
        return (
            [
                message
                for message in self._raw["messages"]
                if message["severity"] == "error"
                or (
                    not self._allow_sorry
                    and message["severity"] == "warning"
                    and message["data"] == "declaration uses 'sorry'"
                )
            ]
            if "messages" in self._raw
            else []
        )

    @classmethod
    def from_str(cls, raw_str: str, code: str, allow_sorry: bool = False) -> Self:
        return cls(json.loads(raw_str), code, allow_sorry)

    def errors(self, max_error_lines: int | None = None) -> list[ErrorInfo]:
        return [
            ErrorInfo(
                line=(pos_line := message["pos"]["line"]),
                code="\n".join(
                    self._code.splitlines()[
                        pos_line - 1 : (
                            message["endPos"]["line"] if message["endPos"] else pos_line
                        )
                    ]
                ),
                message="\n".join(message["data"].splitlines()[:max_error_lines]),
            )
            for message in self._error_messages
        ]

    @classmethod
    def load_if_exists(
        cls, path: Path | str, code: str, allow_sorry: bool = False
    ) -> Self | None:
        return (
            cls.from_str(Path(path).read_text(encoding="utf-8"), code, allow_sorry)
            if Path(path).exists()
            else None
        )

    def save(self, path: Path | str) -> None:
        Path(path).write_text(str(self), encoding="utf-8")

    def __str__(self) -> str:
        return json.dumps(self._raw, ensure_ascii=False)


def verify_proof(
    workspace: Path | str,
    code: str,
    max_attempts: int = 5,
    allow_sorry: bool = False,
) -> ReplOutput | None:
    print(f"Verifying proof:\n{code}")
    print_separator()
    repl_input = json.dumps({"cmd": code}, ensure_ascii=False)
    result = None
    try:
        result = subprocess.run(
            ["lake", "exe", "repl"],
            cwd=workspace,
            input=repl_input,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=1200,
        )
        lean_output = json.loads(result.stdout)
        return ReplOutput(lean_output, code, allow_sorry)
    except subprocess.TimeoutExpired:
        print("Lean verification timed out.")
        return None
    except json.JSONDecodeError:
        print("Failed to decode Lean output as JSON.")
        print("Standard Output:", result and result.stdout)
        print("Standard Error:", result and result.stderr)
        if max_attempts:
            print(f"Retrying verification (remaining attempts: {max_attempts})...")
            return verify_proof(workspace, code, max_attempts - 1, allow_sorry)
        else:
            print("Max attempts reached. Verification failed.")
            return None
