#!/usr/bin/env python3
"""Manual helper: print Notion ``pages.retrieve`` metadata for one page id (not run by pytest).

The coordinator’s **`notion_*`** tools use **hosted MCP + OAuth**; this script is a small
**REST integration** debugger and still requires ``NOTION_TOKEN``.

Usage (from repo root, with ``NOTION_TOKEN`` in the environment)::

    # Prefer activating the venv + .env yourself (avoids any shell quirks):
    source .venv/bin/activate
    set -a && source .env && set +a
    python tests/manual_notion_page_inspect.py dcb83bb2-de37-8335-85de-815d9e0f8bed

    # Or: ``source scripts/dev_shell.sh`` only loads venv/.env; use ``python`` not ``exec``.
    export NOTION_TOKEN="secret_..."
    python tests/manual_notion_page_inspect.py dcb83bb2-de37-8335-85de-815d9e0f8bed

    # Full API object (large; may include doc text in properties — do not paste publicly)
    ./tests/manual_notion_page_inspect.py PAGE_ID --full-json

    # Optional search sample (same API as index refresh)
    ./tests/manual_notion_page_inspect.py PAGE_ID --search-query "corporate engineering"

Requires ``iso-agent[notion]`` / ``notion_client`` installed (project venv).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, cast

# Repo root on path for ``iso_agent``
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from iso_agent.l3_runtime.integrations import notion_client


def _redact_properties_for_preview(raw: dict[str, Any], *, max_chars: int = 4000) -> dict[str, Any]:
    """Return a copy safe to print: property values truncated to ``max_chars`` total JSON."""
    out = dict(raw)
    props = out.get("properties")
    if isinstance(props, dict):
        blob = json.dumps(props, ensure_ascii=False)
        if len(blob) > max_chars:
            out["properties"] = (
                f"<truncated {len(blob)} chars; use --full-json without redaction to inspect locally>"
            )
        else:
            out["properties"] = props
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect Notion pages.retrieve (and optional search) for debugging metadata."
    )
    parser.add_argument("page_id", help="Notion page UUID (with or without hyphens)")
    parser.add_argument(
        "--full-json",
        action="store_true",
        help="Print full pages.retrieve JSON (can be large; may contain document text)",
    )
    parser.add_argument(
        "--search-query",
        metavar="TEXT",
        default="",
        help="If set, also POST /search with this query and page_size=10 (filter=page)",
    )
    parser.add_argument(
        "--redact-properties",
        action="store_true",
        help="With --full-json, truncate properties blob in the printed copy (still inspect locally)",
    )
    args = parser.parse_args()

    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("error: NOTION_TOKEN is empty — export it or run via scripts/dev_shell.sh", file=sys.stderr)
        return 1

    if not notion_client.is_valid_notion_id(args.page_id):
        print("error: invalid page id format", file=sys.stderr)
        return 1

    try:
        pid = notion_client.normalize_notion_page_id(args.page_id)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    client = notion_client.build_notion_client(token)

    print("=== iso_agent summary (fetch_page_summary) ===")
    summary = notion_client.fetch_page_summary(client, page_id=pid)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    ok, diag = notion_client.page_retrieve_diagnostic(client, page_id=pid)
    print("\n=== pages.retrieve diagnostic ===")
    print(f"ok={ok} detail={diag!r}")

    raw = cast(dict[str, Any], client.pages.retrieve(page_id=pid))
    if args.full_json:
        print("\n=== full pages.retrieve ===")
        to_print: dict[str, Any] = raw
        if args.redact_properties:
            to_print = _redact_properties_for_preview(raw)
        print(json.dumps(to_print, indent=2, ensure_ascii=False))
    else:
        print("\n(tip: use --full-json for the complete API object)")

    if args.search_query.strip():
        print("\n=== search (query=%r, page_size=10, filter=page) ===" % (args.search_query.strip(),))
        resp = client.search(
            query=args.search_query.strip(),
            page_size=10,
            filter={"value": "page", "property": "object"},
        )
        if isinstance(resp, dict):
            results = resp.get("results") or []
            print(f"result_count={len(results)}")
            for i, item in enumerate(results[:10], start=1):
                if not isinstance(item, dict):
                    continue
                rid = str(item.get("id", ""))
                title = notion_client.page_plain_title(item)
                parent = item.get("parent", {})
                print(f"  {i}. id={rid} | title={title!r} | parent={parent!r}")
        else:
            print(f"unexpected search response type: {type(resp)!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
