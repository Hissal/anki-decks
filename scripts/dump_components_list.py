#!/usr/bin/env python3
"""One-off helper: dump the sorted unique components from the deck TSV to
`.tmp/components_list.json` so external tooling (e.g. the JS that runs in the
HanziCraft browser tab) can read them.
"""

from __future__ import annotations

import json
from pathlib import Path

from common import REPO_ROOT
from components_common import COMPONENT_DECK_PATH, parse_component_tsv


def main() -> int:
    if not COMPONENT_DECK_PATH.exists():
        print(f"missing {COMPONENT_DECK_PATH}")
        return 1
    _, rows = parse_component_tsv(COMPONENT_DECK_PATH)
    components = sorted({r.component for r in rows})
    out_dir = REPO_ROOT / ".tmp"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "components_list.json"
    out_path.write_text(
        json.dumps(components, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {out_path.relative_to(REPO_ROOT)} with {len(components)} components")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
