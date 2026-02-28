from .base_model import BaseModel


class Game(BaseModel):
    """จัดการข้อมูลเกม"""

    # ------------------------------------------------------------------
    #  Read
    # ------------------------------------------------------------------

    def get_all(self):
        games = self.db.fetchall("SELECT * FROM game")
        for g in games:
            g["logo"] = g.get("game_logo")
        return games

    def get_by_id(self, game_id):
        game = self.db.fetchone(
            "SELECT * FROM game WHERE game_id = %s",
            (game_id,)
        )
        if game:
            game["logo"] = game.get("game_logo")
        return game

    def get_tournaments(self, game_id):
        return self.db.fetchall(
            "SELECT * FROM tournament WHERE game_id = %s ORDER BY date DESC",
            (game_id,)
        )

    def get_teams(self, game_id):
        """ดึงทีมแยกตาม tournament_id ที่ assign ไว้ใน team table"""
        teams = self.db.fetchall("""
            SELECT
                team.team_id, team.team_name, team.logo,
                COALESCE(team.tournament_id, 0) AS tournament_id,
                COALESCE(t.name, 'ไม่มีทัวร์นาเมนต์') AS tournament_name,
                (SELECT COUNT(*) FROM player p2
                 WHERE p2.team_id = team.team_id AND p2.game_id = %s) AS player_count
            FROM player
            JOIN team ON player.team_id = team.team_id
            LEFT JOIN tournament t ON team.tournament_id = t.tournament_id
            WHERE player.game_id = %s
            GROUP BY team.team_id, team.tournament_id
            ORDER BY COALESCE(team.tournament_id, 9999), team.team_name
        """, (game_id, game_id))
        for t in teams:
            t["logo"] = self.to_base64(t.get("logo"))
        return teams

    def get_players(self, game_id):
        """ดึงผู้เล่นแยกตาม tournament"""
        players = self.db.fetchall("""
            SELECT DISTINCT
                player.player_id, player.nickname, player.role, player.image,
                player.team_id,
                team.team_name,
                t.tournament_id, t.name AS tournament_name
            FROM player
            LEFT JOIN team ON player.team_id = team.team_id
            JOIN `match` m ON (m.team1_id = player.team_id OR m.team2_id = player.team_id)
            JOIN tournament t ON m.tournament_id = t.tournament_id
            WHERE player.game_id = %s AND t.game_id = %s
            ORDER BY t.tournament_id, team.team_name, player.nickname
        """, (game_id, game_id))
        for p in players:
            p["image"] = self.to_base64(p.get("image"))
        return players

    def get_recent_matches(self, game_id, limit=10):
        return self.db.fetchall("""
            SELECT m.*, t1.team_name AS team1_name, t2.team_name AS team2_name,
                   t.name AS tournament_name
            FROM `match` m
            JOIN team t1 ON m.team1_id = t1.team_id
            JOIN team t2 ON m.team2_id = t2.team_id
            JOIN tournament t ON m.tournament_id = t.tournament_id
            WHERE t.game_id = %s
            ORDER BY m.match_date DESC, m.match_time DESC
            LIMIT %s
        """, (game_id, limit))

    def count(self):
        row = self.db.fetchone("SELECT COUNT(*) AS total FROM game")
        return row["total"]

    # ------------------------------------------------------------------
    #  Write (Admin)
    # ------------------------------------------------------------------

    def add(self, name, desc=None):
        self.db.execute(
            "INSERT INTO game (game_name, description) VALUES (%s, %s)",
            (name, desc)
        )

    def delete(self, game_id):
        self.db.execute("DELETE FROM game WHERE game_id = %s", (game_id,))