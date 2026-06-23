"""Utilities for recording APMD experiment sessions in the formal design file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    status: str
    summary_filename: str = ""
    figure_filename: str = ""
    note: str = ""


def format_session_record(record: SessionRecord) -> str:
    parts = [f"{record.status}: `{record.session_id}`"]
    if record.summary_filename:
        parts.append(f"summary=`{record.summary_filename}`")
    if record.figure_filename:
        parts.append(f"figure=`{record.figure_filename}`")
    if record.note:
        parts.append(f"note={record.note}")
    return "; ".join(parts)


def _split_markdown_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _format_markdown_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _is_separator_row(cells: list[str]) -> bool:
    return all(set(cell.replace(":", "").replace("-", "").strip()) == set() for cell in cells)


def _updated_cell(existing: str, entry: str, session_id: str) -> tuple[str, bool]:
    if session_id in existing:
        return existing, False

    cleaned = existing.strip()
    if not cleaned or "TBD" in cleaned or "next formal anchor" in cleaned:
        return entry, True
    return f"{cleaned}<br>{entry}", True


def register_session(
    formal_design_path: Path,
    experiment_key: str,
    record: SessionRecord,
) -> bool:
    """Add a session record to the matching formal-design table row.

    Returns True only when the file content changed.
    """
    path = Path(formal_design_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    entry = format_session_record(record)

    target_col_idx: int | None = None
    changed = False
    output: list[str] = []

    for line in lines:
        cells = _split_markdown_row(line)
        if cells is None:
            target_col_idx = None
            output.append(line)
            continue

        lowered = [cell.lower() for cell in cells]
        if "formal rerun session" in lowered:
            target_col_idx = lowered.index("formal rerun session")
            output.append(line)
            continue

        stage_session_cols = [
            i
            for i, cell in enumerate(lowered)
            if cell.startswith("session") and "formal rerun" not in cell
        ]
        if stage_session_cols:
            target_col_idx = stage_session_cols[-1]
            output.append(line)
            continue

        if _is_separator_row(cells):
            output.append(line)
            continue

        if target_col_idx is not None and cells and experiment_key in cells[0]:
            while len(cells) <= target_col_idx:
                cells.append("")
            cells[target_col_idx], changed = _updated_cell(
                cells[target_col_idx],
                entry,
                record.session_id,
            )
            output.append(_format_markdown_row(cells))
            continue

        output.append(line)

    if not changed:
        return False

    trailing_newline = "\n" if path.read_text(encoding="utf-8").endswith("\n") else ""
    path.write_text("\n".join(output) + trailing_newline, encoding="utf-8")
    return True
