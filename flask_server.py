from flask import Flask, send_file, request, jsonify
from flask import abort
from nba_handler import nba_bp
# from nfl_handler import nfl_bp

app = Flask(__name__)

# Track paused state per client_id (can be updated later)
paused_states = {}

@app.route("/select_game")
def select_game_dispatch():
    game_id = request.args.get("gameId")
    client_id = request.args.get("client_id")

    if not game_id or not client_id:
        return jsonify({"error": "Missing gameId or client_id"}), 400

    # Get sport for this client_id (default nba if missing)
    sport = getattr(app, "client_states", {}).get(client_id, {}).get("sport", "nba")

    # Build internal path
    internal_path = f"/{sport}/select_game?gameId={game_id}&client_id={client_id}"

    # Forward internally to the correct blueprint view function
    if sport == "nba":
        # Call nba_bp select_game directly
        with app.test_request_context(internal_path):
            return nba_bp.view_functions['select_game']()
    # elif sport == "nfl":
    #     with app.test_request_context(internal_path):
    #         return nfl_bp.view_functions['select_game']()
    else:
        return jsonify({"error": "Unknown sport"}), 400

@app.route("/api/select_sport")
def select_sport():
    cid   = request.args.get("client_id")
    sport = request.args.get("sport")
    if not cid or sport not in ("nba", "nfl"):
        return jsonify(error="Invalid parameters"), 400
    # ensure state dict exists
    from nba_handler import client_states as nba_states
    from nfl_handler import client_states as nfl_states
    # we keep a single shared client_states in flask_server; assume you merge them or import one
    app.client_states = getattr(app, "client_states", {})
    app.client_states.setdefault(cid, {})["sport"] = sport
    return jsonify(message=f"Sport set to {sport}"), 200

@app.route("/api/current_sport")
def current_sport():
    cid = request.args.get("client_id")
    sport = getattr(app, "client_states", {}).get(cid, {}).get("sport", "nba")
    return jsonify(sport=sport), 200

# Register blueprints with unique URL prefixes
app.register_blueprint(nba_bp, url_prefix='/nba')
# app.register_blueprint(nfl_bp, url_prefix='/nfl')

# Serve index.html at root
@app.route("/")
def index():
    return send_file("index.html")  # Ensure this file is in the same directory

@app.route("/is_paused")
def is_paused():
    client_id = request.args.get("client_id")
    return jsonify({"paused": paused_states.get(client_id, False)})

@app.route("/pause", methods=["POST"])
def pause():
    client_id = request.json.get("client_id")
    paused_states[client_id] = True
    return "Paused", 200

@app.route("/resume", methods=["POST"])
def resume():
    client_id = request.json.get("client_id")
    paused_states[client_id] = False
    return "Resumed", 200

# Optional: root /connect route for compatibility
@app.route("/connect", methods=["POST"])
def connect_root():
    data = request.json
    ssid = data.get("ssid")
    password = data.get("pass")
    if not ssid or not password:
        return "Missing SSID or password", 400
    print(f"[ROOT] Received WiFi config: SSID={ssid}, PASS={password}")
    return "WiFi config received at root", 200

@app.route("/current_mode")
def current_mode():
    client_id = request.args.get("client_id")
    if not client_id or client_id not in app.client_states:
        return jsonify({"error": "Invalid client_id"}), 400
    return jsonify({
        "sport": app.client_states[client_id].get("sport", "unknown")
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

