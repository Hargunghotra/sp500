"""One-shot CLI for GitHub Actions / cron: run a single agent cycle."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure backend package imports resolve when run as `python run_cycle.py`
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import run_cycle  # noqa: E402
from config import (  # noqa: E402
    ALLOW_AFTER_HOURS,
    DATA_DIR,
    GEMINI_API_KEY,
    INITIAL_BALANCE,
    TRADING_SESSION,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one autonomous paper-trading cycle and exit."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even outside US regular market hours (ignores session gate).",
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
        f"Agent cycle starting (force={args.force}, "
        f"trading_session={TRADING_SESSION}, "
        f"allow_after_hours={ALLOW_AFTER_HOURS}, "
        f"has_gemini_key={bool(GEMINI_API_KEY)}, "
        f"initial_balance={INITIAL_BALANCE})"
    )

    result = run_cycle(force=args.force)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        skipped = bool(result.get("skipped"))
        ok = bool(result.get("ok", False))
        executed = result.get("executed_count", 0)
        print("--- cycle summary ---")
        print(f"ok={ok} skipped={skipped} executed={executed}")
        if result.get("reason"):
            print(f"reason={result['reason']}")
        if result.get("error"):
            print(f"error={result['error']}")
        strategy = result.get("strategy") or {}
        if strategy.get("thesis"):
            print(f"thesis={strategy['thesis'][:200]}")
        report = result.get("ai_report") or {}
        if report.get("headline"):
            print(f"report={report['headline']}")
        print(f"data_dir={DATA_DIR}")

    # Soft skip (outside market hours) is success for cron.
    if result.get("skipped"):
        return 0
    if not result.get("ok", False):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
