from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


def print_separator() -> None:
    print("+*" * 20)


def print_with_separator(msgs: list[Any] | None) -> None:
    print(*msgs if msgs else (msgs,), sep="\n" + "-" * 40 + "\n")


def load_content(
    target_dir: Path | str,
    target_file: Path | str = Path("Main.lean"),
) -> str:
    return (Path(target_dir) / target_file).read_text()


def store_content(
    content: str,
    target_dir: Path | str,
    target_file: Path = Path("Main.lean"),
) -> None:
    (Path(target_dir) / target_file).write_text(content)


def remove_import_and_open_and_set_option(
    lean_code: str,
) -> str:
    return "\n".join(
        line
        for line in lean_code.split("\n")
        if not line.strip().startswith("import")
        and not line.strip().startswith("open")
        and not line.strip().startswith("set_option")
    ).lstrip("\n")


def remove_sorry(theorem: str) -> str:
    return theorem.rstrip().removesuffix("sorry").rstrip()


def update_open(lean_header: str, theorem: str) -> str:
    additional_open = next(
        (line for line in theorem.splitlines() if line.startswith("open")), None
    )
    if not additional_open:
        return lean_header
    original_open = next(
        (line for line in lean_header.splitlines() if line.startswith("open")), None
    )
    assert original_open, "No open found in lean header"
    additional_open_set = set(additional_open.replace("open ", "").split())
    original_open_set = set(original_open.replace("open ", "").split())
    opens_to_add = " ".join(additional_open_set - original_open_set)
    return (
        lean_header.replace(original_open, f"{original_open} {opens_to_add}")
        if opens_to_add
        else lean_header
    )


def convert_to_lemma(lemma: str) -> str:
    return lemma.replace("theorem", "lemma")


def convert_to_theorem(lemma: str) -> str:
    return lemma.replace("lemma", "theorem")


def split_header(code: str) -> tuple[str, str]:
    lines = code.split("\n")
    idx = next(
        (
            i
            for i, line in enumerate(lines)
            if line.startswith("lemma") or line.startswith("theorem")
        ),
        0,
    )
    return "\n".join(lines[:idx]), "\n".join(lines[idx:])


split_comments = split_header  # alias


def restore_theorem_statements(proof: str, original: str) -> str:
    return re.sub(
        r"(theorem.*?:= by)", lambda _: original.replace(":= by sorry", ":= by"), proof
    )


def remove_comments(text: str) -> str:
    text = re.sub(r"/-.*?-/", "", text, flags=re.DOTALL)
    return "\n".join(
        filter(
            lambda x: x is not None,  # type: ignore
            [
                re.sub(r"--.*", "", line).rstrip() or None if "-- " in line else line
                for line in text.splitlines()
            ],
        )
    ).strip()


def remove_preceding_comments(text: str) -> str:
    idx = re.search(r"(theorem|lemma)", text)
    return text[idx and idx.start() :]


def extract_first_comment(text: str) -> str | None:
    match = re.search(r"/-+(.*?)-+/", text, flags=re.DOTALL)
    return match.group(1).strip() if match else None


_THEOREM_NAME_PATTERN = re.compile(
    r"^(?P<kw>theorem|lemma)(?P<sp1>\s+)(?P<name>\S+)(?P<sp2>\s)", re.MULTILINE
)


def get_theorem_name(theorem: str) -> str:
    if match := _THEOREM_NAME_PATTERN.search(theorem):
        return match.group("name")
    raise ValueError("Theorem or lemma name not found")


def set_theorem_name(theorem: str, new_name: str) -> str:
    return _THEOREM_NAME_PATTERN.sub(
        lambda m: f"{m.group('kw')}{m.group('sp1')}{new_name}{m.group('sp2')}",
        theorem,
        count=1,
    )


def make_model_url_mapping(model_url_mapping: list[str]) -> dict[str, str]:
    assert len(model_url_mapping) % 2 == 0, (
        "Model URL mapping must have an even number of elements."
    )
    return {
        model_url_mapping[i]: model_url_mapping[i + 1]
        for i in range(0, len(model_url_mapping), 2)
    }
