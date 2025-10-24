from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from prover_agent.runner._base import BaseRunner
from prover_agent.utils import (
    remove_import_and_open_and_set_option,
    remove_sorry,
    update_open,
)

if TYPE_CHECKING:
    import sys
    from typing import Any

    from prover_agent._config import Config

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


@dataclass
class ProofContext:
    cfg: Config
    theorem: str
    log_dir: Path | str
    workspace: Path | str
    runner: BaseRunner
    resume_from: Path | str | None = field(default=None)
    results: dict[str, Any] = field(default_factory=dict)
    lean_header: str = field(init=False)

    def __post_init__(self) -> None:
        self.lean_header = update_open(self.cfg.lean_header, self.theorem)
        th = self.theorem.strip()
        th = remove_import_and_open_and_set_option(th)
        self.theorem = remove_sorry(th)

    def with_new_theorem(self, theorem: str) -> Self:
        return type(self)(
            cfg=self.cfg,
            theorem=theorem,
            log_dir=self.log_dir,
            workspace=self.workspace,
            runner=self.runner,
            resume_from=self.resume_from,
            results=self.results,
        )


@dataclass
class LogSession:
    prefix: str | None = field(default=None)
    suffix: str | None = field(default=None)
    sub_dir: Path | str = field(default=Path(""))

    def get_log_filename(self, base_name: str) -> Path:
        name = base_name
        if self.prefix:
            name = f"{self.prefix}{name}"
        if self.suffix:
            name = name.replace(".", f"{self.suffix}.")
        return Path(self.sub_dir) / name

    def with_prefix(self, prefix: str) -> Self:
        return type(self)(prefix=prefix, suffix=self.suffix, sub_dir=self.sub_dir)

    def with_suffix(self, suffix: str) -> Self:
        return type(self)(prefix=self.prefix, suffix=suffix, sub_dir=self.sub_dir)

    def with_sub_dir(self, sub_dir: Path | str) -> Self:
        return type(self)(prefix=self.prefix, suffix=self.suffix, sub_dir=sub_dir)
