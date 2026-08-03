"""Background scheduler for the autonomous trading agent."""

from __future__ import annotations

import logging
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import AGENT_ENABLED_DEFAULT, AGENT_INTERVAL_MINUTES
from agent import get_status, run_cycle, set_enabled

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _job() -> None:
    status = get_status()
    if not status.get("enabled"):
        return
    if status.get("running"):
        return
    logger.info("Scheduled agent cycle starting")
    run_cycle(force=False)


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler


def next_run_iso() -> str | None:
    if _scheduler is None:
        return None
    job = _scheduler.get_job("ai_trade_agent")
    if not job or not job.next_run_time:
        return None
    return job.next_run_time.isoformat()


def status_payload() -> dict[str, Any]:
    base = get_status()
    return {
        **base,
        "interval_minutes": AGENT_INTERVAL_MINUTES,
        "next_run": next_run_iso(),
        "scheduler_running": bool(_scheduler and _scheduler.running),
    }


def start_scheduler(*, enable_agent: bool | None = None) -> dict[str, Any]:
    global _scheduler

    if enable_agent is None:
        enable_agent = AGENT_ENABLED_DEFAULT
    set_enabled(bool(enable_agent))

    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="America/New_York")
        _scheduler.add_job(
            _job,
            trigger=IntervalTrigger(minutes=AGENT_INTERVAL_MINUTES),
            id="ai_trade_agent",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    if not _scheduler.running:
        _scheduler.start()
        logger.info(
            "Scheduler started (interval=%sm, agent_enabled=%s)",
            AGENT_INTERVAL_MINUTES,
            get_status()["enabled"],
        )

    return status_payload()


def stop_agent() -> dict[str, Any]:
    """Disable trading cycles; keep scheduler process alive for next_run metadata."""
    set_enabled(False)
    return status_payload()


def start_agent() -> dict[str, Any]:
    start_scheduler(enable_agent=True)
    return status_payload()
