"""Annotate retained OTG properties with [otg-only] / [dse-mapped] markers.

Heuristic: a property is [dse-mapped] if its name appears as a property in any
schema under public_api_otg/aiworkload/.  Otherwise it gets [otg-only].

This script writes line-comments above property keys in OTG yaml files, preserving
formatting.  It's idempotent: if a marker is already present, it skips that property.

Run from models/:
    python public_api_otg/scripts/annotate_otg_only.py [--dry-run]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent              # public_api_otg/

# OTG-rooted dirs to annotate (skip aiworkload/, api/, artifacts/, scripts/, top-level).
OTG_DIRS = ("port", "layer1", "device", "control", "result", "common", "config")


def collect_dse_property_names() -> set[str]:
    names: set[str] = set()
    for path in (ROOT / "aiworkload").rglob("*.yaml"):
        try:
            doc = yaml.safe_load(path.read_text())
        except Exception:
            continue
        for schema in (doc.get("components", {}) or {}).get("schemas", {}).values():
            if isinstance(schema, dict):
                for prop in (schema.get("properties") or {}).keys():
                    names.add(prop)
    return names


PROP_PATTERN = re.compile(r"^(\s+)([A-Za-z_][A-Za-z0-9_]*):\s*$")
MARKER_PATTERN = re.compile(r"#\s*\[(otg-only|dse-mapped[^\]]*)\]")


def annotate_file(path: Path, dse_names: set[str], dry_run: bool) -> int:
    """Returns number of new annotations written."""
    text = path.read_text()
    lines = text.splitlines()
    out: list[str] = []
    added = 0

    for i, line in enumerate(lines):
        # Only annotate inside an indented schema's `properties:` block — we
        # cheaply assume indentation >= 8 spaces (component schema property).
        m = PROP_PATTERN.match(line)
        if m and len(m.group(1)) >= 8:
            prev = out[-1] if out else ""
            if MARKER_PATTERN.search(prev):
                out.append(line)
                continue
            indent, prop = m.groups()
            marker = "[dse-mapped]" if prop in dse_names else "[otg-only]"
            out.append(f"{indent}# {marker}")
            added += 1
        out.append(line)

    new_text = "\n".join(out) + ("\n" if text.endswith("\n") else "")
    if not dry_run and added:
        path.write_text(new_text)
    return added


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    dse_names = collect_dse_property_names()
    total = 0
    for d in OTG_DIRS:
        for path in (ROOT / d).rglob("*.yaml"):
            n = annotate_file(path, dse_names, args.dry_run)
            total += n
            if n:
                print(f"{path.relative_to(ROOT)}: +{n}")
    print(f"\nTotal annotations: {total} ({'dry run' if args.dry_run else 'written'})")


if __name__ == "__main__":
    main()
