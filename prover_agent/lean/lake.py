from __future__ import annotations

import fcntl
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from prover_agent.lean._base import ErrorInfo, LeanOutputBase
from prover_agent.utils import print_separator

if TYPE_CHECKING:
    import sys

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


class LakeOutput(LeanOutputBase):
    def __init__(self, raw: str, code: str, allow_sorry: bool = False) -> None:
        super().__init__(raw, code, allow_sorry)
        self._messages = _parse_output(raw)
        self._messages.extend(_detect_apply(code))
        self._messages.sort(key=lambda msg: msg.line)

    @property
    def _error_messages(self) -> list[_Message]:
        return [
            message
            for message in self._messages
            if message.severity == _Severity.ERROR
            or (
                not self._allow_sorry
                and message.severity == _Severity.WARNING
                and "declaration uses 'sorry'" in message.text
            )
        ]

    def errors(self, max_error_lines: int | None = None) -> list[ErrorInfo]:
        return [
            ErrorInfo(
                line=(line := message.line),
                code="\n".join(self._code.splitlines()[line - 1 : line]),
                message="\n".join(message.text.splitlines()[:max_error_lines]),
            )
            for message in self._error_messages
        ]

    @classmethod
    def load_if_exists(
        cls, path: Path | str, code: str, allow_sorry: bool = False
    ) -> Self | None:
        return (
            cls(text, code, allow_sorry)
            if (path := Path(path)).exists()
            and _is_lake_output(text := path.read_text(encoding="utf-8"))
            else None
        )

    def save(self, path: Path | str) -> None:
        Path(path).write_text(self._raw, encoding="utf-8")


def verify_proof(
    workspace: Path | str,
    code: str,
    max_attempts: int = 5,
    allow_sorry: bool = False,
) -> LakeOutput | None:
    print(f"Verifying proof:\n{code}")
    print_separator()
    main_path = Path(workspace) / "Main.lean"
    lock_path = main_path.with_suffix(".lean.lock")

    try:
        with open(lock_path, "a+") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                main_path.write_text(code, encoding="utf-8")
                res = subprocess.run(
                    ["lake", "build"],
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                return LakeOutput(res.stdout, code, allow_sorry)
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)
    except Exception as e:
        print(f"Error during verification attempt: {e}")
        if max_attempts:
            print(f"Retrying verification (remaining attempts: {max_attempts})...")
            return verify_proof(workspace, code, max_attempts - 1, allow_sorry)
        else:
            print("Max attempts reached. Verification failed.")
            return None


# NOTE: Python 3.11+ introduces enum.StrEnum.
# After dropping Python 3.10 support, switch to stdlib StrEnum and remove the shim.
# See:
#   - https://docs.python.org/3/library/enum.html#enum.StrEnum
#   - https://docs.python.org/3.11/whatsnew/3.11.html
class _Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    NOTE = "note"

    def __str__(self) -> str:
        return self.value


_HEADER_RE = re.compile(
    rf"^({'|'.join(_Severity)}):(?:\s+(.+?):(\d+):(\d+):\s*(.*)|\s*(.*))$", re.MULTILINE
)


@dataclass
class _Message:
    line: int
    text: str
    severity: _Severity


def _parse_output(output_raw: str) -> list[_Message]:
    output = output_raw.strip()
    if m := re.search(r"^trace:.*$", output, re.MULTILINE):
        output = output[m.end() :].strip()
    if m := re.search(
        r"^\s*(Some builds logged failures:|Build completed successfully)",
        output,
        re.MULTILINE,
    ):
        output = output[: m.start()].strip()
    matches = list(_HEADER_RE.finditer(output))
    messages = [
        _Message(
            line=int(m.group(3)),
            text=(
                m.group(5).strip()
                + (
                    "\n" + body
                    if (
                        body := output[
                            m.end() : matches[i + 1].start()
                            if i + 1 < len(matches)
                            else len(output)
                        ].strip()
                    )
                    else ""
                )
            ),
            severity=_Severity(m.group(1)),
        )
        for i, m in enumerate(list(_HEADER_RE.finditer(output)))
        if m.group(2)
    ]
    if "Some builds logged failures" in output_raw and not any(
        message.severity == _Severity.ERROR for message in messages
    ):
        messages.append(
            _Message(
                line=1,
                text="Lake reported build failures, but no error messages were found.",
                severity=_Severity.ERROR,
            )
        )
    return messages


def _detect_apply(code: str) -> list[_Message]:
    messages = [
        _Message(
            line=i + 1,
            text="Do not use 'apply?' in proofs.",
            severity=_Severity.ERROR,
        )
        for i, line in enumerate(code.splitlines())
        if "apply?" in line
    ]
    return messages


def _is_lake_output(output: str) -> bool:
    return (not (o := output.strip()).startswith("{")) and len(o.splitlines()) > 1
