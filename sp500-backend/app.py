from flask import Flask, jsonify, request
from flask_cors import CORS
import os

from agent import run_cycle
from analyzer import analyze_ticker
from equity import list_equity, mark_to_market
from assets import normalize_symbol
from ledger import execute_trade, load_portfolio, reset_portfolio, update_position_levels
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
    try:
        book = load_portfolio()
        mtm = mark_to_market(book)
        return jsonify(
            {
                **book,
                "equity": mtm["equity"],
                "positions_value": mtm["positions_value"],
                "unrealized_pnl": mtm["unrealized_pnl"],
                "realized_pnl": mtm.get("realized_pnl", book.get("realized_pnl", 0)),
                "total_pnl": mtm.get("total_pnl"),
                "position_rows": mtm.get("position_rows") or [],
                "mtm": mtm,
            }
        )
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 500


@app.route("/api/portfolio/equity", methods=["GET"])
def portfolio_equity():
    try:
        limit = request.args.get("limit", 500, type=int)
        limit = max(1, min(limit or 500, 2000))
        history = list_equity(limit)
        current = mark_to_market()
        return jsonify({"history": history, "current": current})
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 500


@app.route("/api/portfolio/reset", methods=["POST"])
def portfolio_reset():
    try:
        book = reset_portfolio()
        return jsonify({"portfolio": book, "message": "Portfolio reset to starting capital"})
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 500


@app.route("/api/portfolio/position", methods=["PATCH"])
def portfolio_position():
    data = request.json or {}
    try:
        symbol = normalize_symbol(str(data.get("symbol") or data.get("ticker") or ""))
        if not symbol:
            raise ValueError("symbol is required")
        stop_loss = data.get("stop_loss", None)
        take_profit = data.get("take_profit", None)
        if stop_loss is not None:
            stop_loss = float(stop_loss)
        if take_profit is not None:
            take_profit = float(take_profit)
        book = update_position_levels(
            symbol, stop_loss=stop_loss, take_profit=take_profit
        )
        mtm = mark_to_market(book)
        return jsonify({"portfolio": book, "position_rows": mtm.get("position_rows") or []})
    except (TypeError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 500


@app.route("/api/trade", methods=["POST"])
def trade():
    data = request.json or {}
    try:
        ticker = normalize_symbol(str(data.get("ticker") or ""))
        side = str(data.get("type") or data.get("side") or "").upper()
        price = float(data.get("price"))
        shares = float(data.get("shares"))
        pattern = str(data.get("pattern") or "")
        reasoning = str(data.get("reasoning") or "Manual trade")
        stop_loss = data.get("stop_loss")
        take_profit = data.get("take_profit")
        result = execute_trade(
            ticker,
            side,
            price,
            shares,
            pattern=pattern,
            reasoning=reasoning,
            confidence=None,
            source="manual",
            stop_loss=float(stop_loss) if stop_loss is not None else None,
            take_profit=float(take_profit) if take_profit is not None else None,
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
    if not use_reloader or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_scheduler()


if __name__ == "__main__":
    _boot_scheduler()
    app.run(
        port=5000,
        debug=True,
        use_reloader=os.environ.get("USE_RELOADER", "1") != "0",
    )
