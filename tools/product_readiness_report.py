"""Read-only authored product inventory; no runtime imports or promotion checks."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = "docs/implementation/product-readiness.json"
MAX_BYTES = 131_072
STATUSES = ("partial", "foundation", "not_implemented", "validated_slice")
FRONT_IDS = tuple(f"F{i:02d}" for i in range(1, 14)) + tuple(f"T{i:02d}" for i in range(1, 4))
SOURCE_DOCUMENTS = (
    "documento_mestre_jarvis.md",
    "docs/implementation/implementation-master-map.md",
    "docs/implementation/parallel-implementation-map.md",
    "docs/implementation/unified-gap-and-absorption-backlog.md",
    "docs/implementation/execution-backlog.md",
)
_TOP_KEYS = {"schema_version", "snapshot_date", "evidence_scope", "last_validated_mb",
             "active_mb", "source_documents", "fronts"}
_FRONT_KEYS = {"id", "name", "status", "available", "remaining_acceptance", "evidence"}
_ROOTS = {"docs", "tools", "shared", "services", "engines", "apps", "evolution"}
_EXTENSIONS = {".md", ".py", ".mjs", ".html", ".css", ".json"}
_PRIVATE_PARTS = {".git", ".codex", ".agents", ".aws", ".env", "secrets", "credentials",
                  "private", "runtime", "artifacts", "data", "node_modules", ".venv"}


def _invalid():
    raise ValueError("invalid_product_readiness_inventory")


def _text(value, maximum=512):
    if (type(value) is not str or not 1 <= len(value) <= maximum or value != value.strip()
            or any(unicodedata.category(c) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for c in value)):
        _invalid()


def _safe_path(value, root):
    """Validate lexical and resolved containment before checking file existence."""
    if (type(value) is not str or not 1 <= len(value) <= 240
            or re.fullmatch(r"[A-Za-z0-9_./-]+", value) is None):
        _invalid()
    relative = PurePosixPath(value)
    if (relative.is_absolute() or str(relative) != value
            or any(part in {".", ".."} or part.lower() in _PRIVATE_PARTS
                   or part.startswith(".") for part in relative.parts)
            or relative.suffix.lower() not in _EXTENSIONS
            or (value != SOURCE_DOCUMENTS[0] and relative.parts[0] not in _ROOTS)):
        _invalid()
    try:
        workspace = Path(root).resolve(strict=True)
        target = workspace.joinpath(*relative.parts).resolve(strict=True)
    except OSError:
        _invalid()
    try:
        resolved = target.relative_to(workspace).as_posix()
    except ValueError:
        _invalid()
    # An in-workspace symlink must not disguise a private target, either.
    actual = PurePosixPath(resolved)
    if (any(part.lower() in _PRIVATE_PARTS or part.startswith(".") for part in actual.parts)
            or actual.suffix.lower() not in _EXTENSIONS
            or (resolved != SOURCE_DOCUMENTS[0] and actual.parts[0] not in _ROOTS)
            or not target.is_file()):
        _invalid()
    return target


def _strings(values):
    if type(values) is not list or not 1 <= len(values) <= 8:
        _invalid()
    for value in values:
        _text(value)
    if len(set(values)) != len(values):
        _invalid()


def _milestone(value, statuses):
    if (type(value) is not dict or set(value) != {"id", "status"}
            or type(value["id"]) is not str
            or re.fullmatch(r"MB[1-9][0-9]{1,4}", value["id"]) is None
            or type(value["status"]) is not str or value["status"] not in statuses):
        _invalid()


def validate_inventory(document, *, root=ROOT):
    """Validate structure/reference paths only; never infer truth from file presence."""
    if (type(document) is not dict or set(document) != _TOP_KEYS
            or document["schema_version"] != "jarvis-product-readiness-v1"
            or document["evidence_scope"] != "authored_snapshot"
            or type(document["snapshot_date"]) is not str
            or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", document["snapshot_date"]) is None):
        _invalid()
    try:
        date.fromisoformat(document["snapshot_date"])
    except ValueError:
        _invalid()
    _milestone(document["last_validated_mb"], {"done"})
    if document["active_mb"] is not None:
        _milestone(document["active_mb"], {"ready", "in_progress", "blocked"})
        if document["active_mb"]["id"] == document["last_validated_mb"]["id"]:
            _invalid()
    if (type(document["source_documents"]) is not list
            or tuple(document["source_documents"]) != SOURCE_DOCUMENTS):
        _invalid()
    for value in document["source_documents"]:
        _safe_path(value, root)
    fronts = document["fronts"]
    if type(fronts) is not list or len(fronts) != len(FRONT_IDS):
        _invalid()
    for expected_id, front in zip(FRONT_IDS, fronts, strict=True):
        if (type(front) is not dict or set(front) != _FRONT_KEYS
                or front["id"] != expected_id or type(front["status"]) is not str
                or front["status"] not in STATUSES):
            _invalid()
        _text(front["name"], 80)
        _strings(front["available"])
        _strings(front["remaining_acceptance"])
        _strings(front["evidence"])
        for value in front["evidence"]:
            _safe_path(value, root)
    return document


def _pairs(values):
    output = {}
    for key, value in values:
        if key in output:
            _invalid()
        output[key] = value
    return output


def _constant(_value):
    _invalid()


def load_inventory(path=DEFAULT_INVENTORY, *, root=ROOT):
    if type(path) is not str or not path.startswith("docs/implementation/"):
        _invalid()
    target = _safe_path(path, root)
    # Read only the selected inventory, never the referenced evidence contents.
    if target.suffix != ".json":
        _invalid()
    with target.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        _invalid()
    try:
        document = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_pairs,
                              parse_constant=_constant)
        json.dumps(document, ensure_ascii=False, allow_nan=False).encode("utf-8", "strict")
    except (UnicodeError, ValueError, OverflowError, RecursionError):
        _invalid()
    return validate_inventory(document, root=root)


def build_report(document, *, root=ROOT):
    document = validate_inventory(document, root=root)
    # Copy authored data so callers cannot mutate the inventory through output.
    report = json.loads(json.dumps(document, ensure_ascii=False, allow_nan=False))
    report["schema_version"] = "jarvis-product-readiness-report-v1"
    report["runtime_verified"] = False
    report["product_ready"] = False
    report["counts"] = {
        "product_fronts": 13,
        "transversal_fronts": 3,
        "total_fronts": 16,
        "by_status": {status: sum(front["status"] == status for front in document["fronts"])
                      for status in STATUSES},
    }
    return report


def render_text(report):
    def cell(value):
        return value.replace("\\", "\\\\").replace("|", "\\|").replace("`", "'")

    counts = report["counts"]
    active = report["active_mb"]
    active_text = f"{active['id']} ({active['status']})" if active else "nenhum recorte ativo"
    lines = [
        f"JARVIS — prontidão de produto — snapshot autoral {report['snapshot_date']}",
        "Valida apenas schema e referências existentes; não executa nem verifica o runtime.",
        f"Último recorte validado: {report['last_validated_mb']['id']}. Ativo: {active_text}.",
        "Sistema completo: não pronto; status de slice não é promoção de produto.",
        f"Frentes: {counts['product_fronts']} de produto + "
        f"{counts['transversal_fronts']} transversais.",
        "Contagens: " + ", ".join(f"{key}={value}" for key, value in counts["by_status"].items()),
        "", "| Frente | Estado parcial | Principal aceite restante |", "| --- | --- | --- |",
    ]
    for front in report["fronts"]:
        lines.append(f"| {front['id']} {cell(front['name'])} | {front['status']} | "
                     f"{cell(front['remaining_acceptance'][0])} |")
    lines.extend(["", "Detalhes de baseline, outros aceites e evidência: --format json.",
                  "Fila única: docs/implementation/execution-backlog.md.",
                  "Este inventário não substitui o Documento-Mestre ou os mapas canônicos."])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", default=DEFAULT_INVENTORY,
                        help="Caminho JSON relativo ao workspace; nenhum path privado/externo.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    options = parser.parse_args(argv)
    try:
        report = build_report(load_inventory(options.inventory))
    except (ValueError, OSError, RecursionError, TypeError, KeyError, OverflowError):
        print("invalid_product_readiness_inventory", file=sys.stderr)
        return 2
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="strict")
    if options.format == "json":
        print(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
