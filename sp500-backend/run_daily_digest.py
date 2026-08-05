"""CLI: assemble + email the post-close daily digest (Actions / local)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import (  # noqa: E402
    DATA_DIR,
    DIGEST_ENABLED,
    DIGEST_TO,
    GEMINI_API_KEY,
    SMTP_USER,
)
from digest import run_digest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and email the daily paper-desk digest."
    )
    parser.add_argument(
        "--date",
        default=None,
        help="America/New_York calendar date YYYY-MM-DD (default: today ET).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Gather + brief + print; do not SMTP or update strategy_prev.json.",
    )
    parser.add_argument(
        "--skip-gemini",
        action="store_true",
        help="Use local fallback briefing (no Gemini call).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full result JSON to stdout.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(
        f"Daily digest starting (date={args.date or 'today ET'}, "
        f"dry_run={args.dry_run}, skip_gemini={args.skip_gemini}, "
        f"digest_enabled={DIGEST_ENABLED}, to={DIGEST_TO}, "
        f"has_gemini_key={bool(GEMINI_API_KEY)}, has_smtp_user={bool(SMTP_USER)})"
    )

    result = run_digest(
        day=args.date,
        dry_run=args.dry_run,
        skip_gemini=args.skip_gemini,
    )

    def _out(msg: str) -> None:
        try:
            print(msg)
        except UnicodeEncodeError:
            print(msg.encode("ascii", "replace").decode("ascii"))

    if args.json:
        _out(json.dumps(result, indent=2, default=str))
    else:
        _out("--- digest summary ---")
        _out(f"ok={result.get('ok')} date={result.get('date')} emailed={result.get('emailed')}")
        _out(f"subject={result.get('subject')}")
        briefing = result.get("briefing") or {}
        if briefing.get("headline"):
            _out(f"headline={briefing['headline']}")
        if briefing.get("pnl_blurb"):
            _out(f"pnl={briefing['pnl_blurb']}")
        summary = result.get("facts_summary") or {}
        _out(f"trades={summary.get('trade_count')} open={summary.get('open_positions')}")
        if result.get("error"):
            _out(f"error={result['error']}")
        if args.dry_run and result.get("text_preview"):
            _out("--- text preview ---")
            _out(result["text_preview"])
        _out(f"data_dir={DATA_DIR}")

    if not result.get("ok", False):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
