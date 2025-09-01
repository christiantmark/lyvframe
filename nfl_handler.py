from flask import Blueprint, request, jsonify
import requests
from threading import Lock
import logging

nfl_bp = Blueprint("nfl", __name__, url_prefix="/nfl")
logging.basicConfig(level=logging.DEBUG)

API_BASE = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"

# Single shared state for all clients
client_states = {}
client_lock = Lock()

def reset_client_for_new_game(client_id, client_states):
    """
    Resets the client state when a new game is selected.
    """
    with lock:  # Make sure you have a threading.Lock() called lock in your module
        if client_id in client_states:
            client_states[client_id]["last_shot_index"] = -1
            client_states[client_id]["lastKnownPeriod"] = 0
            client_states[client_id]["gameOverAnnounced"] = False
            client_states[client_id]["delivered_orders"] = set()
            client_states[client_id]["order_numbers_sorted"] = []
            client_states[client_id]["shots_dict"] = {}

@nfl_bp.route("/connect", methods=["GET", "POST"])
def connect_device():
    if request.method == "POST":
        data = request.get_json() or request.form
        ssid = data.get("ssid")
        password = data.get("pass")
    else:
        ssid = request.args.get("ssid")
        password = request.args.get("pass")

    if not ssid or not password:
        return "Missing SSID or password", 400

    logging.info(f"Received WiFi credentials: SSID={ssid}, PASS={password}")
    return "WiFi credentials received", 200

@nfl_bp.route("/games", methods=["GET"])
def get_nfl_games():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Missing date parameter"}), 400

    try:
        from datetime import datetime
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        espn_date = date_obj.strftime("%Y%m%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={espn_date}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return jsonify({"error": f"Failed to fetch schedule: {str(e)}"}), 500

    games = []
    for event in data.get("events", []):
        comp = event.get("competitions", [])[0]
        competitors = comp.get("competitors", [])
        home = next((t for t in competitors if t["homeAway"]=="home"), None)
        away = next((t for t in competitors if t["homeAway"]=="away"), None)
        if home and away:
            games.append({
                "gameId":   event["id"],
                "homeTeam": home["team"]["abbreviation"],
                "awayTeam": away["team"]["abbreviation"],
                "startTime": event.get("date")
            })

    return jsonify(games), 200

@nfl_bp.route("/select_game")
def select_game():
    game_id = request.args.get("gameId")
    cid     = request.args.get("client_id")
    if not game_id or not cid:
        return jsonify(error="Missing gameId or client_id"), 400

    url = f"{API_BASE}/events/{game_id}/competitions/{game_id}/plays?limit=500"
    resp = requests.get(url)
    if resp.status_code != 200:
        return jsonify(error="Failed to fetch plays", status=resp.status_code), resp.status_code

    data      = resp.json()
    raw_plays = data.get("items") or data.get("plays") or []

    simple = []
    for idx, p in enumerate(raw_plays):
        start = p.get("start", {})
        simple.append({
            "text":            p.get("text"),
            "period":          p.get("period", {}).get("number"),
            "clock":           p.get("clock", {}).get("displayValue"),
            "index":           idx,
            "down":            start.get("down"),
            "distance":        start.get("distance"),
            "yardLine":        start.get("yardLine"),
            "yardsToEndzone":  start.get("yardsToEndzone"),
            "downDistanceText":        start.get("downDistanceText"),
            "shortDownDistanceText":   start.get("shortDownDistanceText"),
            "possessionText":          start.get("possessionText"),
            "teamId":                  start.get("team", {}).get("id"),
        })

    with client_lock:
        client_states[cid] = {
            "sport":     "nfl",
            "plays":      simple,
            "last_idx":   -1,
            "paused":     False,
            "gameId":     game_id,
            "just_reset": True,    
        }

    logging.debug("Loaded %d plays for client %s", len(simple), cid)
    reset_client_for_new_game(client_id, client_states)

    return jsonify({
        "status":   "ok",
        "message":  f"Loaded {len(simple)} plays for game {game_id}",
        "sport":    "nfl"
    }), 200

@nfl_bp.route("/current_game")
def current_game_nfl():
    cid = request.args.get("client_id")
    state = client_states.get(cid)
    if not state:
        return jsonify(error="Invalid client_id"), 400
    return jsonify(gameId=state.get("gameId")), 200

@nfl_bp.route("/peek_play")
def peek_play():
    cid = request.args.get("client_id")
    state = client_states.get(cid)
    if not state:
        return jsonify(error="Invalid client_id"), 400

    if state.get("paused"):
        return jsonify(paused=True), 200

    state["last_idx"] += 1
    if state["last_idx"] >= len(state["plays"]):
        return jsonify(message="No new play"), 204

    return jsonify(state["plays"][state["last_idx"]])

import logging

@nfl_bp.route("/next_play")
def next_play():
    cid = request.args.get("client_id")
    state = client_states.get(cid)
    if not state:
        return jsonify(error="Missing or invalid client_id"), 400

    # ⛔ Don’t proceed if paused
    if state.get("paused"):
        return '', 204

    logging.debug(f"Before increment: client {cid} last_idx={state.get('last_idx')}")
    state["last_idx"] += 1
    logging.debug(f"After increment: client {cid} last_idx={state.get('last_idx')}")

    # No more plays?
    if state["last_idx"] >= len(state["plays"]):
        return '', 204

    # Pull out the next play
    play_data = state["plays"][state["last_idx"]]
    # Copy into a payload dict so we can add our flag
    payload = play_data.copy() if isinstance(play_data, dict) else dict(play_data)

    # 🚩 One-time reset injection
    if state.pop("just_reset", False):
        payload["reset"] = True

    return jsonify(payload)

@nfl_bp.route("/pause", methods=["POST"])
def pause_play():
    cid = request.args.get("client_id")
    if not cid:
        return jsonify(error="Missing client_id"), 400
    with client_lock:
        client_states.setdefault(cid, {})["paused"] = True
    return "", 204

@nfl_bp.route("/resume", methods=["POST"])
def resume_play():
    cid = request.args.get("client_id")
    if not cid:
        return jsonify(error="Missing client_id"), 400
    with client_lock:
        client_states.setdefault(cid, {})["paused"] = False
    return "", 204

@nfl_bp.route("/is_paused", methods=["GET"])
def is_paused():
    cid = request.args.get("client_id")
    if not cid:
        return jsonify(error="Missing client_id"), 400
    paused = client_states.get(cid, {}).get("paused", False)
    return jsonify(paused=paused), 200

