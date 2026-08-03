from flask import Flask, jsonify, request
from flask_cors import CORS
import os

from agent import run_cycle
from analyzer import analyze_ticker
from ledger import execute_trade, load_portfolio
from reports import list_reports
from scheduler import start_agent, start_scheduler, status_payload, stop_agent

app = Flask(__name__)
CORS(app)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.json or {}
    ticker = data.get("ticker", "SPY")
    try:
        result = analyze_ticker(str(ticker), include_series=True)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 500


@app.route("/api/portfolio", methods=["GET"])
def portfolio():
    return jsonify(load_portfolio())


@app.route("/api/trade", methods=["POST"])
def trade():
    data = request.json or {}
    try:
        ticker = str(data.get("ticker", "")).upper()
        side = str(data.get("type") or data.get("side") or "").upper()
        price = float(data.get("price"))
        shares = int(data.get("shares"))
        pattern = str(data.get("pattern") or "")
        reasoning = str(data.get("reasoning") or "Manual trade")
        result = execute_trade(
            ticker,
            side,
            price,
            shares,
            pattern=pattern,
            reasoning=reasoning,
            confidence=None,
            source="manual",
        )
        return jsonify(result)
    except (TypeError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 500


@app.route("/api/agent/status", methods=["GET"])
def agent_status():
    return jsonify(status_payload())


@app.route("/api/agent/start", methods=["POST"])
def agent_start():
    return jsonify(start_agent())


@app.route("/api/agent/stop", methods=["POST"])
def agent_stop():
    return jsonify(stop_agent())


@app.route("/api/agent/run-once", methods=["POST"])
def agent_run_once():
    data = request.json or {}
    force = bool(data.get("force", True))
    result = run_cycle(force=force)
    status = status_payload()
    return jsonify({"result": result, "status": status})


@app.route("/api/agent/reports", methods=["GET"])
def agent_reports():
    limit = request.args.get("limit", 50, type=int)
    limit = max(1, min(limit or 50, 200))
    return jsonify({"reports": list_reports(limit)})


def _boot_scheduler() -> None:
    use_reloader = os.environ.get("USE_RELOADER", "1") != "0"
    # With reloader: only the child process should start the scheduler.
    if not use_reloader or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_scheduler()


if __name__ == "__main__":
    _boot_scheduler()
    app.run(
        port=5000,
        debug=True,
        use_reloader=os.environ.get("USE_RELOADER", "1") != "0",
    )
