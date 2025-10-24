from __future__ import annotations

import pickle
from pathlib import Path
from typing import TYPE_CHECKING

from prover_agent.lean._base import ErrorInfo, LeanOutputBase
from prover_agent.utils import print_separator, split_header

if TYPE_CHECKING:
    import sys

    from pantograph.data import CompilationUnit
    from pantograph.message import Message

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


class PantographOutput(LeanOutputBase):
    def __init__(
        self,
        raw: list[CompilationUnit] | CompilationUnit,
        code: str,
        allow_sorry: bool = False,
    ) -> None:
        super().__init__(raw if isinstance(raw, list) else [raw], code, allow_sorry)

    @property
    def _error_messages(self) -> list[Message]:
        from pantograph.message import Severity

        return [
            message
            for unit in self._raw
            for message in unit.messages
            if message.severity == Severity.ERROR
            or (
                not self._allow_sorry
                and message.severity == Severity.WARNING
                and message.kind == "hasSorry"
            )
        ]

    def errors(self, max_error_lines: int | None = None) -> list[ErrorInfo]:
        return [
            ErrorInfo(
                line=(pos_line := message.pos.line),
                code="\n".join(
                    self._code.splitlines()[
                        pos_line - 1 : (
                            message.pos_end.line if message.pos_end else pos_line
                        )
                    ]
                ),
                message="\n".join(message.data.splitlines()[:max_error_lines]),
            )
            for message in self._error_messages
        ]

    @classmethod
    def load_if_exists(
        cls, path: Path | str, code: str, allow_sorry: bool = False
    ) -> Self | None:
        return (
            cls(pickle.loads(out.read_bytes()), code, allow_sorry)
            if (out := (p := Path(path)).with_name(p.name + ".pkl")).exists()
            else None
        )

    def save(self, path: Path | str) -> None:
        (p := Path(path)).with_name(p.name + ".pkl").write_bytes(
            pickle.dumps(self._raw)
        )
        p.write_text(str(self._raw))


def verify_proof(
    workspace: Path | str,
    code: str,
    max_attempts: int = 5,
    allow_sorry: bool = False,
) -> PantographOutput | None:
    from pantograph import Server

    print(f"Verifying proof:\n{code}")
    print_separator()
    header, body = split_header(code)
    name = "".join(w.capitalize() for w in Path(workspace).stem.split("_"))
    try:
        with Server(
            imports=[name],
            project_path=Path(workspace).resolve().as_posix(),
            timeout=2400,
        ) as server:
            server.load_header(header)
            res = server.check_compile(body)
        return PantographOutput(res, code, allow_sorry)
    except Exception as e:
        print(f"Error during verification attempt: {e}")
        if max_attempts:
            print(f"Retrying verification (remaining attempts: {max_attempts})...")
            return verify_proof(workspace, code, max_attempts - 1, allow_sorry)
        else:
            print("Max attempts reached. Verification failed.")
            return None
