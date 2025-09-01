from flask import Flask, Blueprint, jsonify, request, send_file
from datetime import datetime, timezone, timedelta
from threading import Thread, Lock, Event
import requests
import time
import logging
import re
import json
import os
from unidecode import unidecode
from flask_cors import CORS
from datetime import datetime, timezone, timedelta, date
from threading import Thread, Lock, Event


nba_bp = Blueprint('nba', __name__)


NBA_SCHEDULE_URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
NBA_GAME_BASE_URL = "https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{}.json"


client_states = {}
lock = Lock()
paused = False
pause_lock = Lock()
live_mode = False
live_start_time = None
stop_event = Event()


with open(os.path.join(os.path.dirname(__file__), "player_id_name_map.json"), "r") as f:
    player_id_name_map = json.load(f)


def load_schedule_for_date_range(start_date_str, end_date_str, schedule_folder=None):
    """
    Load monthly schedule JSON files for all months covered by start_date_str to end_date_str.
    Returns combined dict with keys as date strings and values as lists of games.
    """
    if schedule_folder is None:
        schedule_folder = os.path.join(os.path.dirname(__file__), "schedules")  # adjust if needed


    def month_range(start: date, end: date):
        current = date(start.year, start.month, 1)
        while current <= end:
            yield current.year, current.month
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)


    start_date = date.fromisoformat(start_date_str)
    end_date = date.fromisoformat(end_date_str)


    combined_games = {}


    for year, month in month_range(start_date, end_date):
        filename = os.path.join(schedule_folder, f"{year}_{month:02d}.json")
        if not os.path.exists(filename):
            print(f"⚠️ Schedule file not found: {filename}, skipping.")
            continue
        with open(filename, "r") as f:
            month_games = json.load(f)
            # Filter only dates in range
            for d_str, games_list in month_games.items():
                d = date.fromisoformat(d_str)
                if start_date <= d <= end_date:
                    if d_str not in combined_games:
                        combined_games[d_str] = []
                    combined_games[d_str].extend(games_list)


    return combined_games


def get_games_from_cdn_schedule(date_str):
    """
    Fetch games from live NBA CDN schedule API for a given date_str (YYYY-MM-DD).
    Returns a list of game dicts if found, else empty list.
    """
    try:
        response = requests.get(NBA_SCHEDULE_URL, timeout=10)
        response.raise_for_status()
        data = response.json()


        games = []
        # The CDN schedule JSON structure has 'league' -> 'standard' -> list of days with games
        for day in data.get("league", {}).get("standard", []):
            if day.get("startDateEastern") == date_str:
                for game in day.get("games", []):
                    games.append({
                        "game_id": game.get("gameId"),
                        "home_team": game.get("hTeam", {}).get("triCode"),
                        "away_team": game.get("vTeam", {}).get("triCode")
                    })
                break
        return games
    except Exception as e:
        print(f"Error fetching live schedule: {e}")
        return []


@nba_bp.route('/')
def serve_index():
    return send_file('index.html')


@nba_bp.route("/test", methods=["GET"])
def test_connection():
    return "Arduino connection successful!"


@nba_bp.route("/connect", methods=["GET", "POST"])
def connect_device():
    if request.method == "POST":
        data = request.get_json() or request.form
        ssid = data.get("ssid")
        password = data.get("pass")
    else:  # GET fallback
        ssid = request.args.get("ssid")
        password = request.args.get("pass")


    if not ssid or not password:
        return "Missing SSID or password", 400


    logging.info(f"Received WiFi credentials: SSID={ssid}, PASS={password}")
    return "WiFi credentials received", 200


@nba_bp.route('/games', methods=['GET'])
def list_games_by_date():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Missing date"}), 400
    try:
        # Validate date format
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400


    # First, try fetching from the live CDN schedule API
    games = get_games_from_cdn_schedule(date_str)


    if not games:
        fallback_games = load_schedule_for_date_range(date_str, date_str)
        if date_str in fallback_games:
            games = fallback_games[date_str]
            print(f"Using fallback schedule files for date {date_str}")


    if not games:
        return jsonify({"error": "No games found for this date"}), 404


    # Return the list of games in a consistent format
    return jsonify([
        {
            "gameId": g.get("game_id") or g.get("gameId"),
            "homeTeam": g.get("home_team") or g.get("homeTeam"),
            "awayTeam": g.get("away_team") or g.get("awayTeam"),
        }
        for g in games
    ])


def fallback_get_tricodes(game_id):
    schedule_folder = os.path.join(os.path.dirname(__file__), "schedules")
    for filename in os.listdir(schedule_folder):
        if filename.endswith(".json"):
            filepath = os.path.join(schedule_folder, filename)
            try:
                with open(filepath, "r") as f:
                    monthly_schedule = json.load(f)
                    for date_str, games_list in monthly_schedule.items():
                        for g in games_list:
                            raw_id = str(g.get("game_id", "")).zfill(len(game_id))
                            if raw_id == game_id:
                                print(f"[fallback] Found game {game_id} in {filename} with {g.get('away_team')} @ {g.get('home_team')}")
                                return g.get("home_team"), g.get("away_team")
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
    print(f"[fallback] Game ID {game_id} not found in any schedule file")
    return None, None


@nba_bp.route('/select_game', methods=['GET'])
def select_game():
    game_id   = request.args.get("gameId")
    client_id = request.args.get("client_id")


    if not game_id or not client_id:
        return jsonify({"error": "Missing gameId or client_id"}), 400


    # Optional overrides
    home_tri = request.args.get("home_tricode")
    away_tri = request.args.get("away_tricode")


    # Init default values
    home_tricode = "HOME"
    away_tricode = "AWAY"


    if home_tri and away_tri:
        home_tricode = home_tri.upper()
        away_tricode = away_tri.upper()
    else:
        try:
            if game_id.startswith("00224"):
                resp = requests.get(NBA_SCHEDULE_URL, timeout=10)
                resp.raise_for_status()
                schedule_data = resp.json()
                for day in schedule_data.get("league", {}).get("standard", []):
                    for g in day.get("games", []):
                        raw_id = str(g.get("gameId") or g.get("game_id", ""))
                        if raw_id.zfill(len(game_id)) == game_id:
                            home_tricode = g["hTeam"]["triCode"]
                            away_tricode = g["vTeam"]["triCode"]
                            raise StopIteration
        except StopIteration:
            pass
        except Exception as e:
            print(f"⚠️ Failed to fetch from CDN: {e}")


    if home_tricode in ["HOME", "", None] or away_tricode in ["AWAY", "", None]:
        home, away = fallback_get_tricodes(game_id)
        if home and away:
            home_tricode = home
            away_tricode = away
            print(f"[LOCAL] Found fallback teams for {game_id}: {away} @ {home}")
        else:
            print(f"[LOCAL] Game ID {game_id} not found in local schedules")


    if client_id in client_states:
        old_thread = client_states[client_id]["fetch_thread"]
        if old_thread and old_thread.is_alive():
            client_states[client_id]["stop_event"].set()
            old_thread.join()


    stop_event = Event()


    # Reset client state, start indexing at 1 here:
    client_states[client_id] = {
        "sport":                "nba",
        "game_id":              game_id,
        "shots_dict":           {},
        "order_numbers_sorted": [],
        "delivered_orders":     set(),
        "seq_counter":          1,         # <-- start indexing at 1
        "seq_map":              {},
        "stop_event":           stop_event,
        "home_tricode":         home_tricode,
        "away_tricode":         away_tricode,
        "just_reset":           True
    }


    new_thread = Thread(target=fetch_shots_loop, args=(client_id, game_id, stop_event), daemon=True)
    client_states[client_id]["fetch_thread"] = new_thread
    new_thread.start()


    return jsonify({
        "status": "ok",
        "message": f"Started tracking game {game_id} for client {client_id}",
        "home_tricode": home_tricode,
        "away_tricode": away_tricode,
        "sport": "nba"
    })


@nba_bp.route('/select_live_game', methods=['GET'])
def select_live_game():
    print("→ [ENTRY] select_live_game handler hit")
    client_id = request.args.get("client_id")
    if not client_id:
        return jsonify({"error": "Missing client_id"}), 400


    game_id = get_active_game_id()
    if not game_id:
        return jsonify({"error": "No active NBA game in progress"}), 400


    print(f"🔴 Live mode activated for client {client_id}, game: {game_id}")


    # Initialize client if new
    if client_id not in client_states:
        client_states[client_id] = {
            "sport": "nba",
            "game_id": None,
            "last_index": -1,
            "shots_dict": {},
            "order_numbers_sorted": [],
            "fetch_thread": None,
            "delivered_orders": set(),
            "stop_event": Event(),
            "home_tricode": "HOME",
            "away_tricode": "AWAY"
        }


    # Stop old thread if running
    old_thread = client_states[client_id]["fetch_thread"]
    if old_thread and old_thread.is_alive():
        client_states[client_id]["stop_event"].set()
        old_thread.join()


    # Fetch and store live game tricodes
    try:
        scoreboard = requests.get(
            "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
            timeout=10
        ).json()
        for g in scoreboard.get("scoreboard", {}).get("games", []):
            if g.get("gameId") == game_id:
                client_states[client_id]["home_tricode"] = g["hTeam"]["triCode"]
                client_states[client_id]["away_tricode"] = g["vTeam"]["triCode"]
                print(f"→ [DEBUG] Live tricodes for {client_id}: away_tricode={client_states[client_id]['away_tricode']}, home_tricode={client_states[client_id]['home_tricode']}")
                break
    except Exception as e:
        print(f"⚠️ Could not fetch live game tricodes: {e}")


    # Reset state
    client_states[client_id].update({
        "sport": "nba",
        "game_id": game_id,
        "last_index": -1,
        "shots_dict": {},
        "order_numbers_sorted": [],
        "delivered_orders": set()
    })


    # Start new fetch thread
    stop_event = client_states[client_id]["stop_event"]
    stop_event.clear()
    new_thread = Thread(target=fetch_shots_loop, args=(client_id, game_id, stop_event), daemon=True)
    client_states[client_id]["fetch_thread"] = new_thread
    new_thread.start()


    return jsonify({
        "status": "ok",
        "message": f"Started tracking live game {game_id} for client {client_id}",
        "homeTeam": client_states[client_id]["home_tricode"],
        "awayTeam": client_states[client_id]["away_tricode"]
    })


@nba_bp.route('/current_game')
def current_game():
    client_id = request.args.get('client_id')
    print(f"/current_game called with client_id={client_id}")


    if not client_id or client_id not in client_states:
        print(f"Client ID {client_id} not found, returning 404")
        return "Client ID not found", 404
   
    # Return current game id or data for that client
    game_id = client_states[client_id].get('game_id', '')
    return jsonify({"game_id": game_id})

@nba_bp.route('/current_sport')
def current_sport():
    client_id = request.args.get('client_id')
    sport = client_states.get(client_id, {}).get('sport', 'nba')
    return jsonify({"sport": sport})


@nba_bp.route('/pause', methods=['POST'])
def pause():
    data = request.get_json(force=True)
    client_id = data.get('client_id')
    if not client_id:
        return jsonify({"error": "Missing client_id"}), 400


    if client_id not in client_states:
        client_states[client_id] = {}


    client_states[client_id]['paused'] = True
    print(f"⏸️ System paused for client {client_id}")
    return jsonify({"status": "paused"})


@nba_bp.route('/resume', methods=['POST'])
def resume():
    data = request.get_json(force=True)
    client_id = data.get('client_id')
    if not client_id:
        return jsonify({"error": "Missing client_id"}), 400


    if client_id not in client_states:
        client_states[client_id] = {}


    client_states[client_id]['paused'] = False
    print(f"▶️ System resumed for client {client_id}")
    return jsonify({"status": "running"})


@nba_bp.route('/is_paused', methods=['GET'])
def is_paused():
    client_id = request.args.get('client_id')
    if not client_id:
        return jsonify({"error": "Missing client_id"}), 400


    paused = client_states.get(client_id, {}).get('paused', False)
    return jsonify({"paused": paused})


def parse_iso8601_clock(clock_str):
    """Convert ISO 8601 PT#M#S format to MM:SS string."""
    match = re.match(r'PT(\d+)M([\d.]+)S', clock_str)
    if match:
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        return f"{minutes:02}:{int(seconds):02}"
    return "00:00"


def normalize_player_name(name: str) -> str:
    return unidecode(name)


def replace_special_chars(s):
    replacements = {
        'ö': 'o',
        'Ö': 'O',
        'ä': 'a',
        'Ä': 'A',
        'ü': 'u',
        'Ü': 'U',
        'ß': 'ss'
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s


def fetch_nba_cdn_boxscore(game_id):
    url = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }


    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()


    game = data.get('game', {})
    home = game.get('homeTeam', {})
    away = game.get('awayTeam', {})


    def extract_starters(team):
        starters = []
        players = team.get('players', [])
        for p in players:
            if p.get('starter') == '1':
                stats = p.get('statistics', {})
                starters.append({
                    "name": p.get('name'),
                    "position": p.get('position'),
                    "points": stats.get('points', 0),
                    "rebounds": stats.get('reboundsTotal', 0),
                    "assists": stats.get('assists', 0)
                })
        return starters


    home_starters = extract_starters(home)
    away_starters = extract_starters(away)


    return {
        "home_team": home.get('teamTricode', ''),
        "home_starters": home_starters,
        "away_team": away.get('teamTricode', ''),
        "away_starters": away_starters,
    }


def get_starters_for_game(game_id):
    try:
        return fetch_nba_cdn_boxscore(game_id)
    except requests.HTTPError as e:
        print(f"HTTP error fetching boxscore: {e}")
        return None
    except Exception as e:
        print(f"Error fetching boxscore: {e}")
        return None


@nba_bp.route('/starters', methods=['GET'])
def starters():
    game_id = request.args.get('gameId')
    if not game_id:
        return jsonify({"error": "Missing gameId"}), 400
   
    data = get_starters_for_game(game_id)
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "Failed to fetch starters"}), 500


@nba_bp.route('/pop_shot', methods=['POST'])
def pop_shot():
    data = request.get_json()
    client_id = data.get("client_id")
    shot_index = data.get("shot_index")


    if not client_id or client_id not in client_states:
        return jsonify({"error": "Missing or invalid client_id"}), 400
    if shot_index is None:
        return jsonify({"error": "Missing shot_index"}), 400


    with lock:
        client = client_states[client_id]
        current_last = client.get("last_index", -1)
        if shot_index > current_last:
            client["last_index"] = shot_index


            # Find UID with seq_map value matching shot_index
            seq_map = client.get("seq_map", {})
            uid_to_pop = None
            for uid, seq in seq_map.items():
                if seq == shot_index:
                    uid_to_pop = uid
                    break


            if uid_to_pop:
                client["delivered_orders"].add(uid_to_pop)


    return jsonify({"status": "ok", "last_index": client_states[client_id]["last_index"]})


@nba_bp.route('/get_active_players', methods=['GET'])
def get_active_players():
    client_id = request.args.get("client_id")
    if not client_id or client_id not in client_states:
        return jsonify({"error": "Invalid or missing client_id"}), 400


    active = client_states[client_id].get("on_court_players", {})
    return jsonify({ "active_players": { team: sorted(list(players)) for team, players in active.items() } })

@nba_bp.route("/player_map")
def player_map():
    return jsonify(player_id_name_map)

@nba_bp.route('/player_stats')
def player_stats():
    game_id = request.args.get("gameId")
    player_id = request.args.get("playerId")

    if not game_id or not player_id:
        return jsonify({"error": "Missing gameId or playerId"}), 400

    player_id_int = int(player_id)

    try:
        url = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return jsonify({"error": f"Failed to fetch boxscore: {e}"}), 500

    # Combine all players from both teams
    all_players = []
    for team_key in ["homeTeam", "awayTeam"]:
        team = data.get("game", {}).get(team_key, {})
        players_list = team.get("players", [])
        if isinstance(players_list, dict):
            players_list = list(players_list.values())
        for p in players_list:
            p["team"] = team.get("teamTricode")
            all_players.append(p)

    # Search by personId (correct field)
    for p in all_players:
        if p.get("personId") == player_id_int:
            stats = p.get("statistics", {})
            return jsonify({
                "name": p.get("name"),
                "team": p.get("team"),
                "position": p.get("position"),
                "jerseyNum": p.get("jerseyNum"),
                "points": stats.get("points", 0),
                "rebounds": stats.get("reboundsTotal", 0),
                "assists": stats.get("assists", 0),
                "steals": stats.get("steals", 0),
                "blocks": stats.get("blocks", 0),
                "turnovers": stats.get("turnovers", 0),
                "fgMade": stats.get("fieldGoalsMade", 0),
                "fgAttempted": stats.get("fieldGoalsAttempted", 0),
                "fgPct": stats.get("fieldGoalsPercentage", 0),
                "threePtMade": stats.get("threePointersMade", 0),
                "threePtAttempted": stats.get("threePointersAttempted", 0),
                "threePtPct": stats.get("threePointersPercentage", 0),
                "ftMade": stats.get("freeThrowsMade", 0),
                "ftAttempted": stats.get("freeThrowsAttempted", 0),
                "ftPct": stats.get("freeThrowsPercentage", 0),
                "minutes": stats.get("minutes", "PT0M0S")
            })

    return jsonify({"error": "Player not found in boxscore"}), 404


@nba_bp.route('/next_shot', methods=['GET'])
def next_shot():
    client_id = request.args.get("client_id")
    if not client_id:
        return jsonify({"error":"Missing client_id"}), 400


    client = client_states.get(client_id)
    if not client:
        return jsonify({"error":"Invalid client_id"}), 400
    if client.get("paused"):
        return '', 204


    if client.pop("just_reset", False):
        return jsonify({"reset": True}), 200


    with lock:
        orders    = client.get("order_numbers_sorted", [])
        shots     = client.get("shots_dict", {})
        delivered = client.get("delivered_orders", set())


        if not orders:
            return '', 204


        next_uid = next((uid for uid in orders if uid not in delivered), None)
        if next_uid is None:
            return '', 204


        delivered.add(next_uid)


        seq_map = client.setdefault("seq_map", {})
        if next_uid not in seq_map:
            seq_map[next_uid] = client.get("seq_counter", 0)
            client["seq_counter"] = seq_map[next_uid] + 1
        index = seq_map[next_uid]


    shot = shots.get(next_uid)
    if not shot:
        return jsonify({"error": "Shot data missing for uid"}), 500


    clock  = parse_iso8601_clock(shot.get("clock","")) if shot.get("clock") else ""
    player = unidecode(shot.get("player",""))
    desc   = unidecode(shot.get("description",""))


    payload = {
        "index":        index,
        "player":       player,
        "description":  desc,
        "team":         shot["team"],
        "result":       shot["result"],
        "color":        shot["color"],
        "x":            transform_x(shot["x"]),
        "y":            transform_y(shot["y"]),
        "timeActual":   shot["timeActual"],
        "scoreHome":    shot["scoreHome"],
        "scoreAway":    shot["scoreAway"],
        "home_team":    client.get("home_tricode"),
        "away_team":    client.get("away_tricode"),
        "clock":        clock,
        "period":       shot["period"],
        "isThreePoint": shot.get("isThreePoint", False),
        "isDunk":       shot.get("isDunk", False),
        "onCourt":      shot.get("onCourt", {"home": [], "away": []}),
        "gameId":       client.get("gameId"),
        "actionNumber": shot.get("actionNumber")
    }


    return jsonify(payload)


@nba_bp.route('/peek_shot', methods=['GET'])
def peek_shot():
    client_id = request.args.get("client_id")
    print(f"📥 /peek_shot request received | client_id: {client_id}")


    if not client_id:
        print("❌ Missing client_id")
        return jsonify({"error": "Missing client_id"}), 400


    client = client_states.get(client_id)
    if not client:
        print(f"❌ Invalid client_id: {client_id}")
        return jsonify({"error": "Invalid client_id"}), 400


    if client.get("paused", False):
        print(f"⏸️ Client {client_id} is paused")
        return jsonify({"paused": True, "message": "Client is paused"}), 200


    if client.pop("just_reset", False):
        print(f"🔄 Client {client_id} was just reset")
        return jsonify({"reset": True}), 200


    with lock:
        orders = client.get("order_numbers_sorted", [])
        shots = client.get("shots_dict", {})
        delivered = client.get("delivered_orders", set())


        if not orders:
            print(f"📭 No orders for client {client_id}")
            return '', 204


        next_uid = next((uid for uid in orders if uid not in delivered), None)
        if next_uid is None:
            print(f"✅ All shots delivered for client {client_id}")
            return '', 204


        seq_map = client.setdefault("seq_map", {})
        if next_uid not in seq_map:
            seq_map[next_uid] = client.get("seq_counter", 0)
            client["seq_counter"] = seq_map[next_uid] + 1
        index = seq_map[next_uid]


        shot = shots.get(next_uid)
        if not shot:
            print(f"❌ Shot not found for UID {next_uid} | client: {client_id}")
            return jsonify({"error": "Shot not found for UID"}), 500


        home_team = client.get("home_tricode", "HOME")
        away_team = client.get("away_tricode", "AWAY")


    clock  = parse_iso8601_clock(shot.get("clock", "")) if shot.get("clock") else ""
    player = unidecode(shot.get("player", ""))
    desc   = unidecode(shot.get("description", ""))


    print(f"📤 Sending shot to client {client_id} | UID: {next_uid}, Player: {player}, Result: {shot['result']}, Index: {index}")


    return jsonify({
        "index":        index,
        "player":       player,
        "description":  desc,
        "team":         shot["team"],
        "result":       shot["result"],
        "color":        shot["color"],
        "x":            transform_x(shot["x"]),
        "y":            transform_y(shot["y"]),
        "timeActual":   shot["timeActual"],
        "scoreHome":    shot["scoreHome"],
        "scoreAway":    shot["scoreAway"],
        "clock":        clock,
        "period":       shot["period"],
        "home_team":    home_team,
        "away_team":    away_team,
        "isThreePoint": shot.get("isThreePoint", False),
        "onCourt":      shot.get("onCourt", {"home": [], "away": []}),
        "gameId":       client.get("gameId"),
        "actionNumber": shot.get("actionNumber")
    })




def fetch_shots_loop(client_id, game_id, stop_event):
    import time
    import requests


    def abbreviate_name(name):
        parts = name.split()
        if len(parts) == 0:
            return name
        first_initial = parts[0][0] + "." if parts[0] else ""
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        return f"{first_initial} {last_name}".strip()


    # Mappings
    name_to_pid = {v: int(k) for k, v in player_id_name_map.items()}
    pid_to_name = {int(k): v for k, v in player_id_name_map.items()}
    abbr_to_pid = {abbreviate_name(name): pid for name, pid in name_to_pid.items()}
    team_basket_side = {}
    left_basket = (10, 15)
    right_basket = (38, 15)
    game_url = f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json"

    with lock:
        client_states[client_id]["gameId"] = game_id

    # --- Initialize starters ---
    try:
        starter_info = fetch_nba_cdn_boxscore(game_id)
        home_tricode = starter_info["home_team"]
        away_tricode = starter_info["away_team"]


        with lock:
            client_states[client_id]["home_tricode"] = home_tricode
            client_states[client_id]["away_tricode"] = away_tricode
            client_states[client_id]["on_court_players"] = {
                home_tricode: set(name_to_pid.get(p["name"]) for p in starter_info["home_starters"] if p["name"] in name_to_pid),
                away_tricode: set(name_to_pid.get(p["name"]) for p in starter_info["away_starters"] if p["name"] in name_to_pid),
            }


            client_states[client_id]["shots_dict"] = {}
            client_states[client_id]["order_numbers_sorted"] = []
            client_states[client_id]["next_shot_index"] = 1
            client_states[client_id]["sub_log"] = []


        print(f"Initialized starters for {client_id}: {home_tricode}, {away_tricode}")
    except Exception as e:
        print(f"Error fetching starters for {client_id}: {e}")
        with lock:
            client_states[client_id]["on_court_players"] = {}
            client_states[client_id]["shots_dict"] = {}
            client_states[client_id]["order_numbers_sorted"] = []
            client_states[client_id]["next_shot_index"] = 1
            client_states[client_id]["sub_log"] = []


    # --- Main fetch loop ---
    while not stop_event.is_set():
        with lock:
            home_tricode = client_states[client_id]["home_tricode"]
            away_tricode = client_states[client_id]["away_tricode"]
            sub_log = client_states[client_id].setdefault("sub_log", [])


        try:
            resp = requests.get(game_url, timeout=10)
            resp.raise_for_status()
            actions = resp.json().get("game", {}).get("actions", [])


            added = 0
            for a in actions:
                action_type = a.get("actionType")
                team = a.get("teamTricode", "").strip().upper()


                # 🔁 SUBSTITUTION
                if action_type == "substitution":
                    sub_type  = a.get("subType", "").lower()
                    team      = a.get("teamTricode", "").strip().upper()
                    player_id = a.get("personId")            # ← use this instead of name-looking
                    if not team or sub_type not in ("in", "out") or player_id is None:
                        continue

                    with lock:
                        on_court = client_states[client_id]["on_court_players"].setdefault(team, set())

                        if sub_type == "out":
                            on_court.discard(player_id)

                        elif sub_type == "in":
                            on_court.add(player_id)

                        client_states[client_id]["on_court_players"][team] = on_court

                        # keep a short log for debugging
                        msg = f"SUB {team} {sub_type.upper()}: personId={player_id}"
                        sub_log = client_states[client_id].setdefault("sub_log", [])
                        sub_log.append(msg)
                        if len(sub_log) > 5:
                            sub_log.pop(0)
                        print(f"🔁 {msg}")
                    continue

                # --- SHOT PROCESSING ---
                result = a.get("shotResult")
                shooter = a.get("playerNameI") or a.get("playerName")
                period = a.get("period", 1)
                if not (result and a.get("timeActual") and shooter and team):
                    continue


                is_jump = action_type in ("2pt", "3pt") and "x" in a and "y" in a
                is_dunk = a.get("subType") == "DUNK" and result == "Made"
                is_ft = action_type == "freethrow" and result in ("Made", "Missed")
                if not (is_jump or is_dunk or is_ft):
                    continue


                shot_uid = f"{a['timeActual']}_{shooter}_{result}_{period}"
                with lock:
                    if shot_uid in client_states[client_id]["shots_dict"]:
                        continue


                if is_jump or is_dunk:
                    raw_x = int(round((a["x"] / 100.0) * 47))
                    raw_y = 31 - int(round((a["y"] / 100.0) * 31))
                    led_x, led_y = transform_coordinates(raw_x, raw_y)
                    if result == "Made":
                        if period <= 2:
                            team_basket_side[team] = right_basket if team == home_tricode else left_basket
                        else:
                            team_basket_side[team] = left_basket if team == home_tricode else right_basket
                    x, y = led_x, led_y
                    color = "blue" if is_dunk else ("green" if result == "Made" else "red")
                else:
                    if team in team_basket_side:
                        x, y = team_basket_side[team]
                    else:
                        cond = (period <= 2 and team == home_tricode) or (period >= 3 and team == away_tricode)
                        x, y = left_basket if cond else right_basket
                    color = "green" if result == "Made" else "red"


                with lock:
                    live_on = client_states[client_id]["on_court_players"]
                on_court_snap = {
                    "home": sorted(
                        [{"id": pid, "name": abbreviate_name(pid_to_name.get(pid, str(pid)))} for pid in live_on.get(home_tricode, [])],
                        key=lambda p: p["name"]
                    ),
                    "away": sorted(
                        [{"id": pid, "name": abbreviate_name(pid_to_name.get(pid, str(pid)))} for pid in live_on.get(away_tricode, [])],
                        key=lambda p: p["name"]
                    )
                }


                with lock:
                    idx = client_states[client_id]["next_shot_index"]
                    client_states[client_id]["shots_dict"][shot_uid] = {
                        "x": x, "y": y,
                        "result": result,
                        "timeActual": a["timeActual"],
                        "player": shooter,
                        "team": team,
                        "scoreHome": a.get("scoreHome", "N/A"),
                        "scoreAway": a.get("scoreAway", "N/A"),
                        "description": a.get("description", ""),
                        "clock": a.get("clock", ""),
                        "period": period,
                        "color": color,
                        "shot_index": idx,
                        "isThreePoint": action_type == "3pt",
                        "isDunk": is_dunk,
                        "onCourt": on_court_snap,
                        "gameId": game_id,
                        "actionNumber": a.get("actionNumber")
                    }
                    client_states[client_id]["next_shot_index"] += 1
                    added += 1


            if added:
                with lock:
                    shots = client_states[client_id]["shots_dict"]
                    client_states[client_id]["order_numbers_sorted"] = sorted(
                        shots.keys(),
                        key=lambda uid: shots[uid]["shot_index"]
                    )
                    print(f"📅 Client {client_id}: Cached {added} new shots")


        except Exception as e:
            print(f"❌ Client {client_id} - Error fetching shots: {e}")


        time.sleep(5)


def transform_coordinates(x, y):
    return x, y


def transform_x(x):
    return x


def transform_y(y):
    return y


def check_if_game_over(game_id):
    return False


def get_active_game_id():
    try:
        scoreboard=requests.get("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",timeout=10).json()
        games=scoreboard.get("scoreboard",{}).get("games",[])
        if not games:
            print("⚠️ No games found in scoreboard.")
            return None
        live_status_keywords=["1st Qtr","2nd Qtr","3rd Qtr","4th Qtr","OT","In Progress"]
        for g in games:
            game_id=g.get("gameId")
            status=g.get("gameStatusText","").strip()
            away=g.get("awayTeam",{}).get("teamTricode","???")
            home=g.get("homeTeam",{}).get("teamTricode","???")
            print(f"📝 Game {game_id} | {away} @ {home} | Status: {status}")
            if any(keyword in status for keyword in live_status_keywords):
                print(f"✅ Found live game: {game_id} ({away} @ {home})")
                return game_id
        print("❌ No live game found.")
    except Exception as e:
        print(f"⚠️ Error getting active game id: {e}")
    return None


app = Flask(__name__)
app.register_blueprint(nba_bp)
CORS(app)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)





