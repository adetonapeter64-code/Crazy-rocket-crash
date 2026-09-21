"""
app.py - play-money crash game server (deployment-ready, flat folder).
"""
import os
import time
import threading
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO

from crash_logic import generate_server_seed, hash_seed, generate_crash_point
import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

db.init_db()

round_state = {
    "phase": "waiting",
    "multiplier": 1.0,
    "crash_point": None,
    "server_seed": None,
    "server_seed_hash": None,
    "client_seed": "public-seed",
    "nonce": 0,
    "bets": {},
    "start_time": None,
}
lock = threading.Lock()
STARTING_BALANCE = 100000  # play money in cents = 1000.00 credits


def broadcast_state():
    socketio.emit("state_update", {
        "phase": round_state["phase"],
        "multiplier": round(round_state["multiplier"], 2),
    })


def game_loop():
    while True:
        with lock:
            round_state["phase"] = "waiting"
            round_state["multiplier"] = 1.0
            round_state["bets"] = {}
            round_state["server_seed"] = generate_server_seed()
            round_state["server_seed_hash"] = hash_seed(round_state["server_seed"])
            round_state["nonce"] += 1
        socketio.emit("round_waiting", {
            "seed_hash": round_state["server_seed_hash"],
            "countdown": 5,
        })
        time.sleep(5)

        with lock:
            round_state["crash_point"] = generate_crash_point(
                round_state["server_seed"], round_state["client_seed"], round_state["nonce"]
            )
            round_state["phase"] = "running"
            round_state["start_time"] = time.time()
        socketio.emit("round_started", {})

        while True:
            elapsed = time.time() - round_state["start_time"]
            with lock:
                round_state["multiplier"] = 2.71828 ** (0.06 * elapsed)
                if round_state["multiplier"] >= round_state["crash_point"]:
                    round_state["multiplier"] = round_state["crash_point"]
                    round_state["phase"] = "crashed"
                    done = True
                else:
                    done = False
            broadcast_state()
            if done:
                break
            time.sleep(0.1)

        socketio.emit("round_crashed", {
            "crash_point": round_state["crash_point"],
            "server_seed": round_state["server_seed"],
        })
        time.sleep(3)


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/api/join", methods=["POST"])
def join():
    session_id = str(uuid.uuid4())
    db.create_player(session_id, f"Player-{session_id[:5]}", STARTING_BALANCE)
    player = db.get_player(session_id)
    return jsonify({"session_id": session_id, "balance": player["balance"]})


@app.route("/api/bet", methods=["POST"])
def place_bet():
    data = request.json or {}
    session_id = data.get("session_id")
    try:
        amount = int(data.get("amount", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid bet amount"}), 400
    player = db.get_player(session_id)

    with lock:
        if player is None:
            return jsonify({"error": "Unknown session, please refresh"}), 400
        if round_state["phase"] != "waiting":
            return jsonify({"error": "Betting is closed for this round"}), 400
        if amount <= 0 or amount > player["balance"]:
            return jsonify({"error": "Invalid bet amount"}), 400
        if session_id in round_state["bets"]:
            return jsonify({"error": "Already bet this round"}), 400
        try:
            new_balance = db.change_balance(session_id, -amount, "bet_placed", round_state["nonce"])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        round_state["bets"][session_id] = {"amount": amount, "cashed_out": False, "cashout_at": None}
    return jsonify({"balance": new_balance})


@app.route("/api/cashout", methods=["POST"])
def cashout():
    data = request.json or {}
    session_id = data.get("session_id")

    with lock:
        bet = round_state["bets"].get(session_id)
        if round_state["phase"] != "running":
            return jsonify({"error": "No active round to cash out from"}), 400
        if not bet or bet["cashed_out"]:
            return jsonify({"error": "No active bet to cash out"}), 400
        current_multiplier = round_state["multiplier"]
        winnings = int(bet["amount"] * current_multiplier)
        bet["cashed_out"] = True
        bet["cashout_at"] = current_multiplier
        new_balance = db.change_balance(session_id, winnings, "cash_out", round_state["nonce"])
    return jsonify({"balance": new_balance, "cashed_out_at": current_multiplier, "winnings": winnings})


# Start the game loop when the server loads (works locally and under gunicorn)
threading.Thread(target=game_loop, daemon=True).start()

if __name__ == "__main__":
    socketio.run(app, port=5000, allow_unsafe_werkzeug=True)
