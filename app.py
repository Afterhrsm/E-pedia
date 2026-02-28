from flask import Flask, render_template, request, redirect, session
import mysql.connector
import base64

import os

app = Flask(__name__)
app.secret_key = "secret123"


# ================= DATABASE =================

def get_db():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASS", ""),
        database=os.environ.get("DB_NAME", "esport_db")
    )


# ================= IMAGE =================

def blob_to_base64(data):
    if not data:
        return None
    if isinstance(data, (bytes, bytearray)):
        return base64.b64encode(data).decode("utf-8")
    if isinstance(data, str):
        return data
    return None


# ================= HELPERS =================

def get_user_id(cursor, username):
    cursor.execute("SELECT user_id FROM users WHERE username=%s", (username,))
    u = cursor.fetchone()
    return u["user_id"] if u else None


def get_user_favorites(cursor, user_id):
    cursor.execute("SELECT item_type, item_id FROM favorite WHERE user_id=%s", (user_id,))
    favs = {"team": set(), "player": set(), "game": set()}
    for f in cursor.fetchall():
        if f["item_type"] in favs:
            favs[f["item_type"]].add(f["item_id"])
    return favs


# ================= LOGIN =================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        db.close()
        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            return redirect("/admin" if user["role"] == "admin" else "/")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ================= HOME =================

@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM game")
    games = cursor.fetchall()

    cursor.execute("SELECT * FROM team")
    teams_data = cursor.fetchall()

    cursor.execute("""
        SELECT tournament.*, game.game_name
        FROM tournament
        JOIN game ON tournament.game_id = game.game_id
    """)
    tournaments = cursor.fetchall()

    cursor.execute("""
        SELECT player.*, team.team_name, game.game_name
        FROM player
        LEFT JOIN team ON player.team_id = team.team_id
        LEFT JOIN game ON player.game_id = game.game_id
    """)
    players_all = cursor.fetchall()

    for g in games:
        g["logo"] = g.get("game_logo")

    for t in teams_data:
        t["logo"] = blob_to_base64(t.get("logo"))

    for p in players_all:
        p["image"] = blob_to_base64(p.get("image"))

    user_id = get_user_id(cursor, session["user"])
    favs = get_user_favorites(cursor, user_id) if user_id else {"team": set(), "player": set(), "game": set()}

    db.close()

    return render_template("index.html",
        games=games,
        teams=teams_data,
        tournaments=tournaments,
        players_all=players_all,
        favs=favs,
    )


# ================= GAME DETAIL =================

@app.route("/game/<int:id>")
def game_detail(id):
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM game WHERE game_id=%s", (id,))
    game = cursor.fetchone()

    if not game:
        db.close()
        return "Game not found"

    game["logo"] = game.get("game_logo")

    cursor.execute("SELECT * FROM tournament WHERE game_id=%s ORDER BY date DESC", (id,))
    game_tournaments = cursor.fetchall()

    cursor.execute("""
        SELECT team.*, COUNT(player.player_id) as player_count
        FROM team
        JOIN player ON player.team_id = team.team_id
        WHERE player.game_id = %s
        GROUP BY team.team_id
    """, (id,))
    game_teams = cursor.fetchall()
    for t in game_teams:
        t["logo"] = blob_to_base64(t.get("logo"))

    cursor.execute("""
        SELECT player.*, team.team_name
        FROM player
        LEFT JOIN team ON player.team_id = team.team_id
        WHERE player.game_id = %s
    """, (id,))
    game_players = cursor.fetchall()
    for p in game_players:
        p["image"] = blob_to_base64(p.get("image"))

    cursor.execute("""
        SELECT m.*, t1.team_name AS team1_name, t2.team_name AS team2_name,
               tr.name AS tournament_name
        FROM `match` m
        LEFT JOIN team t1 ON m.team1_id = t1.team_id
        LEFT JOIN team t2 ON m.team2_id = t2.team_id
        LEFT JOIN tournament tr ON m.tournament_id = tr.tournament_id
        WHERE tr.game_id = %s
        ORDER BY m.match_date DESC, m.match_time DESC
        LIMIT 10
    """, (id,))
    game_matches = cursor.fetchall()

    total_prize = 0

    user_id = get_user_id(cursor, session["user"])
    is_fav = False
    if user_id:
        cursor.execute("SELECT 1 FROM favorite WHERE user_id=%s AND item_type='game' AND item_id=%s", (user_id, id))
        is_fav = cursor.fetchone() is not None
    db.close()

    return render_template("game_detail.html",
        game=game,
        is_fav=is_fav,
        game_tournaments=game_tournaments,
        game_teams=game_teams,
        game_players=game_players,
        game_matches=game_matches,
        total_prize=total_prize,
    )


# ================= TEAMS =================

@app.route("/teams")
def teams():
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM team")
    teams_data = cursor.fetchall()
    db.close()

    for t in teams_data:
        t["logo"] = blob_to_base64(t.get("logo"))

    return render_template("teams.html", teams=teams_data)


# ================= TEAM DETAIL =================

@app.route("/team/<int:id>")
def team_detail(id):
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM team WHERE team_id=%s", (id,))
    team = cursor.fetchone()

    if not team:
        db.close()
        return "Team not found", 404

    cursor.execute("""
        SELECT player.*, game.game_name 
        FROM player 
        LEFT JOIN game ON player.game_id = game.game_id 
        WHERE player.team_id=%s
    """, (id,))
    players = cursor.fetchall()

    cursor.execute("""
        SELECT DISTINCT game.game_id, game.game_name, game.game_logo 
        FROM player 
        JOIN game ON player.game_id = game.game_id 
        WHERE player.team_id=%s
    """, (id,))
    team_games = cursor.fetchall()

    # ดึง tournaments ที่ทีมนี้เข้าร่วม (ผ่านผู้เล่น)
    cursor.execute("""
        SELECT DISTINCT tr.tournament_id, tr.name, tr.location, tr.date,
                        tr.prize_pool, g.game_name, g.game_logo
        FROM tournament tr
        JOIN `match` m ON m.tournament_id = tr.tournament_id
        LEFT JOIN game g ON tr.game_id = g.game_id
        WHERE m.team1_id = %s OR m.team2_id = %s
        ORDER BY tr.date DESC
    """, (id, id))
    tournaments = cursor.fetchall()

    team["logo"] = blob_to_base64(team.get("logo"))
    for p in players:
        p["image"] = blob_to_base64(p.get("image"))
    for g in team_games:
        g["logo"] = g.get("game_logo")

    user_id = get_user_id(cursor, session["user"])
    is_fav_team = False
    fav_players = set()
    if user_id:
        cursor.execute("SELECT 1 FROM favorite WHERE user_id=%s AND item_type='team' AND item_id=%s", (user_id, id))
        is_fav_team = cursor.fetchone() is not None
        cursor.execute("SELECT item_id FROM favorite WHERE user_id=%s AND item_type='player'", (user_id,))
        fav_players = {r["item_id"] for r in cursor.fetchall()}
    db.close()

    return render_template("team_detail.html",
                           team=team,
                           players=players,
                           games=team_games,
                           tournaments=tournaments,
                           is_fav_team=is_fav_team,
                           fav_players=fav_players)


# ================= PLAYER DETAIL =================

@app.route("/player/<int:id>")
def player_detail(id):
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT player.*, team.team_name, game.game_name 
        FROM player 
        LEFT JOIN team ON player.team_id = team.team_id
        LEFT JOIN game ON player.game_id = game.game_id
        WHERE player.player_id=%s
    """, (id,))
    player = cursor.fetchone()

    if not player:
        db.close()
        return "Player not found", 404

    player["image"] = blob_to_base64(player.get("image"))
    player["cover"] = player.get("cover_image")

    user_id = get_user_id(cursor, session["user"])
    is_fav = False
    if user_id:
        cursor.execute("SELECT 1 FROM favorite WHERE user_id=%s AND item_type='player' AND item_id=%s", (user_id, id))
        is_fav = cursor.fetchone() is not None
    db.close()

    return render_template("player_detail.html", player=player, is_fav=is_fav)


# ================= TOURNAMENTS =================

@app.route("/tournaments")
def tournaments():
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT tournament.*, game.game_name 
        FROM tournament 
        LEFT JOIN game ON tournament.game_id = game.game_id
    """)
    tournaments_data = cursor.fetchall()
    db.close()

    return render_template("tournaments.html", tournaments=tournaments_data)


# ================= TOURNAMENT DETAIL =================

@app.route("/tournament/<int:id>")
def tournament_detail(id):
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT tournament.*, game.game_name
        FROM tournament
        LEFT JOIN game ON tournament.game_id = game.game_id
        WHERE tournament.tournament_id=%s
    """, (id,))
    tournament = cursor.fetchone()

    if not tournament:
        db.close()
        return "Tournament not found", 404

    cursor.execute("""
        SELECT m.*,
               t1.team_name AS team1_name, t1.logo AS team1_logo,
               t2.team_name AS team2_name, t2.logo AS team2_logo
        FROM `match` m
        LEFT JOIN team t1 ON m.team1_id = t1.team_id
        LEFT JOIN team t2 ON m.team2_id = t2.team_id
        WHERE m.tournament_id = %s
        ORDER BY m.match_date, m.match_time
    """, (id,))
    matches = cursor.fetchall()

    user_id = get_user_id(cursor, session["user"])
    user_votes = {}
    vote_counts = {}

    if user_id:
        cursor.execute("SELECT match_id, team_id FROM vote WHERE user_id=%s", (user_id,))
        for v in cursor.fetchall():
            user_votes[v["match_id"]] = v["team_id"]

    cursor.execute("SELECT match_id, team_id, COUNT(*) as cnt FROM vote GROUP BY match_id, team_id")
    for v in cursor.fetchall():
        if v["match_id"] not in vote_counts:
            vote_counts[v["match_id"]] = {}
        vote_counts[v["match_id"]][v["team_id"]] = v["cnt"]

    db.close()

    for m in matches:
        m["team1_logo"] = blob_to_base64(m.get("team1_logo"))
        m["team2_logo"] = blob_to_base64(m.get("team2_logo"))

    return render_template("tournament_detail.html",
        tournament=tournament,
        matches=matches,
        user_votes=user_votes,
        vote_counts=vote_counts,
        user_id=user_id
    )


# ================= VOTE =================

@app.route("/vote/<int:match_id>/<int:team_id>", methods=["POST"])
def vote(match_id, team_id):
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    user_id = get_user_id(cursor, session["user"])

    if not user_id:
        db.close()
        return redirect("/")

    cursor.execute("SELECT tournament_id FROM `match` WHERE match_id=%s", (match_id,))
    match = cursor.fetchone()
    tournament_id = match["tournament_id"] if match else 1

    try:
        cursor.execute("""
            INSERT INTO vote (match_id, user_id, team_id)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE team_id=%s
        """, (match_id, user_id, team_id, team_id))
        db.commit()
    except:
        db.rollback()

    db.close()
    return redirect(f"/tournament/{tournament_id}")


# ================= FAVORITES =================

@app.route("/favorite/<item_type>/<int:item_id>", methods=["POST"])
def toggle_favorite(item_type, item_id):
    if "user" not in session:
        return redirect("/login")
    if item_type not in ("team", "player", "game"):
        return redirect("/")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    user_id = get_user_id(cursor, session["user"])

    if user_id:
        cursor.execute(
            "SELECT favorite_id FROM favorite WHERE user_id=%s AND item_type=%s AND item_id=%s",
            (user_id, item_type, item_id)
        )
        existing = cursor.fetchone()
        if existing:
            cursor.execute("DELETE FROM favorite WHERE favorite_id=%s", (existing["favorite_id"],))
        else:
            cursor.execute(
                "INSERT INTO favorite (user_id, item_type, item_id) VALUES (%s, %s, %s)",
                (user_id, item_type, item_id)
            )
        db.commit()
    db.close()

    next_url = request.form.get("next", "/")
    return redirect(next_url)


# ================= PROFILE =================

@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE username=%s", (session["user"],))
    user = cursor.fetchone()
    user_id = user["user_id"] if user else None

    fav_teams, fav_players, fav_games = [], [], []

    if user_id:
        cursor.execute("""
            SELECT t.team_id, t.team_name, t.logo
            FROM favorite f JOIN team t ON f.item_id = t.team_id
            WHERE f.user_id=%s AND f.item_type='team'
        """, (user_id,))
        fav_teams = cursor.fetchall()
        for t in fav_teams:
            t["logo"] = blob_to_base64(t.get("logo"))

        cursor.execute("""
            SELECT p.player_id, p.nickname, p.role, p.image, t.team_name
            FROM favorite f
            JOIN player p ON f.item_id = p.player_id
            LEFT JOIN team t ON p.team_id = t.team_id
            WHERE f.user_id=%s AND f.item_type='player'
        """, (user_id,))
        fav_players = cursor.fetchall()
        for p in fav_players:
            p["image"] = blob_to_base64(p.get("image"))

        cursor.execute("""
            SELECT g.game_id, g.game_name, g.game_logo
            FROM favorite f JOIN game g ON f.item_id = g.game_id
            WHERE f.user_id=%s AND f.item_type='game'
        """, (user_id,))
        fav_games = cursor.fetchall()

    db.close()

    return render_template("profile.html",
        user=user,
        fav_teams=fav_teams,
        fav_players=fav_players,
        fav_games=fav_games
    )


# ================= ADMIN PANEL =================

@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return "Access Denied"

    tab = request.args.get("tab", "dashboard")
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total FROM users")
    users_count = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as total FROM game")
    games_count = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as total FROM team")
    teams_count = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as total FROM player")
    players_count = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as total FROM tournament")
    tournaments_count = cursor.fetchone()["total"]

    cursor.execute("SELECT * FROM users")
    users_list = cursor.fetchall()
    cursor.execute("SELECT * FROM game")
    games_list = cursor.fetchall()
    cursor.execute("SELECT * FROM team")
    teams_list = cursor.fetchall()
    cursor.execute("""
        SELECT player.*, team.team_name, game.game_name
        FROM player 
        LEFT JOIN team ON player.team_id = team.team_id
        LEFT JOIN game ON player.game_id = game.game_id
    """)
    players_list = cursor.fetchall()
    cursor.execute("""
        SELECT tournament.*, game.game_name
        FROM tournament LEFT JOIN game ON tournament.game_id = game.game_id
    """)
    tournaments_list = cursor.fetchall()

    cursor.execute("""
        SELECT m.*, t1.team_name AS team1_name, t2.team_name AS team2_name,
               tr.name AS tournament_name
        FROM `match` m
        LEFT JOIN team t1 ON m.team1_id = t1.team_id
        LEFT JOIN team t2 ON m.team2_id = t2.team_id
        LEFT JOIN tournament tr ON m.tournament_id = tr.tournament_id
        ORDER BY m.match_date DESC, m.match_time DESC
    """)
    matches_list = cursor.fetchall()
    db.close()

    data = {
        "users": users_count, "games": games_count,
        "teams": teams_count, "players": players_count,
        "tournaments": tournaments_count,
        "users_list": users_list, "games_list": games_list,
        "teams_list": teams_list, "players_list": players_list,
        "tournaments_list": tournaments_list,
        "matches_list": matches_list
    }

    return render_template("admin.html", tab=tab, data=data)


# ================= ADD =================

@app.route("/admin/add_game", methods=["POST"])
def add_game():
    db = get_db()
    cursor = db.cursor()
    name  = request.form["name"]
    desc  = request.form.get("desc")
    genre = request.form.get("genre")
    cursor.execute("INSERT INTO game (game_name, description, genre) VALUES (%s,%s,%s)", (name, desc, genre))
    db.commit()
    db.close()
    return redirect("/admin?tab=games")


@app.route("/admin/add_team", methods=["POST"])
def add_team():
    db = get_db()
    cursor = db.cursor()
    name          = request.form["name"]
    short_name    = request.form.get("short_name")
    description   = request.form.get("description")
    founded_year  = request.form.get("founded_year") or None
    tournament_id = request.form.get("tournament_id") or None
    brand_color   = request.form.get("brand_color") or "#ff3c1e"  # ← NEW
    logo          = None
    if "logo" in request.files:
        f = request.files["logo"]
        if f.filename:
            logo = f.read()
    cursor.execute(
        "INSERT INTO team (team_name, short_name, logo, description, founded_year, tournament_id, brand_color) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (name, short_name, logo, description, founded_year, tournament_id, brand_color)
    )
    db.commit()
    db.close()
    return redirect("/admin?tab=teams")


@app.route("/admin/add_player", methods=["POST"])
def add_player():
    db = get_db()
    cursor = db.cursor()
    nickname    = request.form["nickname"]
    role        = request.form.get("role")
    team_id     = request.form.get("team_id") or None
    game_id     = request.form.get("game_id") or None
    bio         = request.form.get("bio")
    instagram   = request.form.get("instagram")
    youtube     = request.form.get("youtube")
    cover_image = request.form.get("cover_image")
    nationality = request.form.get("nationality") or "TH"
    achievements= request.form.get("achievements")
    image       = None
    if "image" in request.files:
        f = request.files["image"]
        if f.filename:
            image = f.read()
    cursor.execute(
        "INSERT INTO player (nickname, role, team_id, game_id, bio, image, instagram, youtube, cover_image, nationality, achievements) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (nickname, role, team_id, game_id, bio, image, instagram, youtube, cover_image, nationality, achievements)
    )
    db.commit()
    db.close()
    return redirect("/admin?tab=players")


@app.route("/admin/add_tournament", methods=["POST"])
def add_tournament():
    db = get_db()
    cursor = db.cursor()
    name     = request.form["name"]
    game_id  = request.form.get("game_id") or None
    location = request.form.get("location")
    date     = request.form.get("date") or None
    cursor.execute(
        "INSERT INTO tournament (name, game_id, location, date) VALUES (%s,%s,%s,%s)",
        (name, game_id, location, date)
    )
    db.commit()
    db.close()
    return redirect("/admin?tab=tournaments")


@app.route("/admin/add_match", methods=["POST"])
def add_match():
    db = get_db()
    cursor = db.cursor()
    tournament_id = request.form.get("tournament_id") or None
    team1_id      = request.form.get("team1_id") or None
    team2_id      = request.form.get("team2_id") or None
    match_date    = request.form.get("match_date") or None
    match_time    = request.form.get("match_time") or None
    cursor.execute("""
        INSERT INTO `match` (tournament_id, team1_id, team2_id, match_date, match_time)
        VALUES (%s,%s,%s,%s,%s)
    """, (tournament_id, team1_id, team2_id, match_date, match_time))
    db.commit()
    db.close()
    return redirect("/admin?tab=tournaments")


@app.route("/admin/update_score/<int:match_id>", methods=["POST"])
def update_score(match_id):
    data        = request.get_json()
    team1_score = data.get("team1_score")
    team2_score = data.get("team2_score")
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE `match` SET team1_score=%s, team2_score=%s WHERE match_id=%s",
        (team1_score, team2_score, match_id)
    )
    db.commit()
    db.close()
    return "", 200


# ================= DELETE =================

@app.route("/admin/delete_user/<int:id>")
def delete_user(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE user_id=%s", (id,))
    db.commit()
    db.close()
    return redirect("/admin?tab=users")

@app.route("/admin/delete_game/<int:id>")
def delete_game(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM game WHERE game_id=%s", (id,))
    db.commit()
    db.close()
    return redirect("/admin?tab=games")


# ================= EDIT =================

@app.route("/admin/edit_team/<int:id>", methods=["POST"])
def edit_team(id):
    db = get_db()
    cursor = db.cursor()
    name          = request.form["name"]
    short_name    = request.form.get("short_name")
    description   = request.form.get("description")
    founded_year  = request.form.get("founded_year") or None
    tournament_id = request.form.get("tournament_id") or None
    brand_color   = request.form.get("brand_color") or "#ff3c1e"  # ← NEW
    logo          = None
    if "logo" in request.files:
        f = request.files["logo"]
        if f.filename:
            logo = f.read()
    if logo:
        cursor.execute(
            "UPDATE team SET team_name=%s, short_name=%s, logo=%s, description=%s, founded_year=%s, tournament_id=%s, brand_color=%s WHERE team_id=%s",
            (name, short_name, logo, description, founded_year, tournament_id, brand_color, id)
        )
    else:
        cursor.execute(
            "UPDATE team SET team_name=%s, short_name=%s, description=%s, founded_year=%s, tournament_id=%s, brand_color=%s WHERE team_id=%s",
            (name, short_name, description, founded_year, tournament_id, brand_color, id)
        )
    db.commit()
    db.close()
    return redirect("/admin?tab=teams")


@app.route("/admin/edit_player/<int:id>", methods=["POST"])
def edit_player(id):
    db = get_db()
    cursor = db.cursor()
    nickname    = request.form["nickname"]
    role        = request.form.get("role")
    team_id     = request.form.get("team_id") or None
    game_id     = request.form.get("game_id") or None
    bio         = request.form.get("bio")
    instagram   = request.form.get("instagram")
    youtube     = request.form.get("youtube")
    cover_image = request.form.get("cover_image")
    nationality = request.form.get("nationality") or "TH"
    achievements= request.form.get("achievements")
    image       = None
    if "image" in request.files:
        f = request.files["image"]
        if f.filename:
            image = f.read()
    if image:
        cursor.execute(
            "UPDATE player SET nickname=%s, role=%s, team_id=%s, game_id=%s, bio=%s, image=%s, instagram=%s, youtube=%s, cover_image=%s, nationality=%s, achievements=%s WHERE player_id=%s",
            (nickname, role, team_id, game_id, bio, image, instagram, youtube, cover_image, nationality, achievements, id)
        )
    else:
        cursor.execute(
            "UPDATE player SET nickname=%s, role=%s, team_id=%s, game_id=%s, bio=%s, instagram=%s, youtube=%s, cover_image=%s, nationality=%s, achievements=%s WHERE player_id=%s",
            (nickname, role, team_id, game_id, bio, instagram, youtube, cover_image, nationality, achievements, id)
        )
    db.commit()
    db.close()
    return redirect("/admin?tab=players")


@app.route("/admin/delete_team/<int:id>")
def delete_team(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM team WHERE team_id=%s", (id,))
    db.commit()
    db.close()
    return redirect("/admin?tab=teams")

@app.route("/admin/delete_player/<int:id>")
def delete_player(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM player WHERE player_id=%s", (id,))
    db.commit()
    db.close()
    return redirect("/admin?tab=players")

@app.route("/admin/delete_tournament/<int:id>")
def delete_tournament(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM tournament WHERE tournament_id=%s", (id,))
    db.commit()
    db.close()
    return redirect("/admin?tab=tournaments")


# ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)