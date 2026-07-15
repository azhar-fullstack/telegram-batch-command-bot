"""Generate Telegram /concept command blocks from TSV/CSV rows.

Logic ported from batch-tsv.htm.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConceptRow:
    """One spreadsheet row with generated command block."""

    index: int
    name: str
    type: str
    commands: str
    thumbnail: str = ""


def _detect_dialect(text: str) -> csv.Dialect:
    sample = text[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters="\t,;")
    except csv.Error:
        return csv.excel_tab


def _read_rows(text: str) -> list[dict[str, str]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    dialect = _detect_dialect(text)
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows: list[dict[str, str]] = []
    for raw in reader:
        row = {str(k).strip().lower(): (v or "").strip() for k, v in raw.items() if k}
        rows.append(row)
    return rows


def _concept_type(type_value: str) -> str:
    upper = type_value.upper()
    if "LORA" in upper:
        return "lora"
    if "INVERSION" in upper:
        return "inversion"
    return "style"


def _generate_commands(row: dict[str, str]) -> str:
    type_value = (row.get("type") or "").strip().upper()
    nsfw = (row.get("nsfw") or "").strip().lower()
    name = row.get("name") or ""
    tags = row.get("tags") or ""
    huggingface = row.get("huggingface") or ""
    info = row.get("info") or ""
    token = row.get("token") or ""
    thumbnail = row.get("thumbnail") or ""
    triggers = row.get("triggers") or ""
    description = row.get("description") or ""
    shardgroup = row.get("shardgroup") or ""
    family = row.get("family") or ""

    if not name:
        return ""

    commands = ""

    if "SDXL" in type_value:
        concept_type = _concept_type(type_value)
        commands += f"/concept /new:{name} {concept_type} {huggingface}\n;;;\n"
        commands += f"/concept /shardgroup:{name} {shardgroup or 'SDXL'}\n;;;\n"
        commands += f"/concept /family:{name} {family or 'SDXL'}\n;;;\n"
    elif "SD15" in type_value:
        commands += f"/concept /new:{name} {_concept_type(type_value)} {huggingface}\n;;;\n"
        commands += f"/concept /family:{name} {family or 'SD15'}\n;;;\n"
        commands += f"/concept /info:{name} {info}\n;;;\n"
    elif "HUNY" in type_value:
        commands += f"/concept /new:{name} {_concept_type(type_value)} {huggingface}\n;;;\n"
        commands += f"/concept /family:{name} {family or 'Huny'}\n;;;\n"
    elif "WAN" in type_value:
        commands += f"/concept /new:{name} {_concept_type(type_value)} {huggingface}\n;;;\n"
        commands += f"/concept /family:{name} {family or 'Wan'}\n;;;\n"
    elif "FLUX2" in type_value:
        commands += f"/concept /new:{name} {_concept_type(type_value)} {huggingface}\n;;;\n"
        commands += f"/concept /family:{name} {family or 'Flux2'}\n;;;\n"
    elif "FLUX" in type_value:
        commands += f"/concept /new:{name} {_concept_type(type_value)} {huggingface}\n;;;\n"
        commands += f"/concept /family:{name} {family or 'Flux'}\n;;;\n"
    elif "ZIB" in type_value:
        commands += f"/concept /new:{name} {_concept_type(type_value)} {huggingface}\n;;;\n"
        commands += f"/concept /family:{name} {family or 'Zimage'}\n;;;\n"
    elif "LTX2" in type_value:
        commands += f"/concept /new:{name} {_concept_type(type_value)} {huggingface}\n;;;\n"
        commands += f"/concept /family:{name} {family or 'Ltx2'}\n;;;\n"
    elif "ZIT" in type_value:
        commands += f"/concept /new:{name} {_concept_type(type_value)} {huggingface}\n;;;\n"
        commands += f"/concept /family:{name} {family or 'Zimage'}\n;;;\n"
    elif "QWEN" in type_value:
        commands += f"/concept /new:{name} {_concept_type(type_value)} {huggingface}\n;;;\n"
        commands += f"/concept /family:{name} {family or 'Qwen'}\n;;;\n"
    elif "IDEOGRAM" in type_value:
        commands += f"/concept /new:{name} {_concept_type(type_value)} {huggingface}\n;;;\n"
        commands += f"/concept /family:{name} {family or 'Ideogram'}\n;;;\n"
    elif "CHROMA" in type_value:
        commands += f"/concept /new:{name} {_concept_type(type_value)} {huggingface}\n;;;\n"
        commands += f"/concept /family:{name} {family or 'Chroma'}\n;;;\n"
    elif "ANIMA" in type_value:
        commands += f"/concept /new:{name} {_concept_type(type_value)} {huggingface}\n;;;\n"
        commands += f"/concept /family:{name} {family or 'Anima'}\n;;;\n"

    if nsfw == "yes":
        commands += f"/concept /nsfw:{name} \n;;;\n"
    if info:
        commands += f"/concept /info:{name} {info}\n;;;\n"
    if token:
        commands += f"/concept /token:{name} {token}\n;;;\n"
    if tags:
        commands += f"/concept /addtag:{name} {tags}\n;;;\n"
    if triggers:
        commands += f"/concept /triggers:{name} {triggers}\n;;;\n"
    if description:
        commands += f"/concept /description:{name} {description}\n;;;\n"
    if thumbnail:
        commands += f"/concept /example:{name} {thumbnail}\n\n"

    return commands


def load_concepts_from_text(text: str) -> list[ConceptRow]:
    rows = _read_rows(text)
    concepts: list[ConceptRow] = []
    for index, row in enumerate(rows):
        name = (row.get("name") or "").strip()
        if not name:
            continue
        commands = _generate_commands(row)
        if not commands.strip():
            continue
        concepts.append(
            ConceptRow(
                index=index,
                name=name,
                type=(row.get("type") or "").strip(),
                commands=commands,
                thumbnail=(row.get("thumbnail") or "").strip(),
            )
        )
    return concepts


def load_concepts_from_file(path: str | Path) -> list[ConceptRow]:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8-sig")
    return load_concepts_from_text(text)


def split_command_block(commands: str) -> list[str]:
    """Split a block on ;;; separators into individual commands to send."""
    parts: list[str] = []
    for chunk in commands.split(";;;"):
        for line in chunk.splitlines():
            line = line.strip()
            if line:
                parts.append(line)
    return parts
