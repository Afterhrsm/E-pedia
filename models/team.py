from .base_model import BaseModel


class Team(BaseModel):
    """จัดการข้อมูลทีม"""

    # ------------------------------------------------------------------
    #  Read
    # ------------------------------------------------------------------

    def get_all(self):
        teams = self.db.fetchall("SELECT * FROM team")
        for t in teams:
            t["logo"] = self.to_base64(t.get("logo"))
        return teams

    def get_by_id(self, team_id):
        team = self.db.fetchone(
            "SELECT * FROM team WHERE team_id = %s",
            (team_id,)
        )
        if team:
            team["logo"] = self.to_base64(team.get("logo"))
        return team

    def get_players(self, team_id):
        """ดึง players ทั้งหมดในทีม พร้อม game info"""
        players = self.db.fetchall("""
            SELECT player.*, game.game_name
            FROM player
            LEFT JOIN game ON player.game_id = game.game_id
            WHERE player.team_id = %s
        """, (team_id,))
        for p in players:
            p["image"] = self.to_base64(p.get("image"))
        return players

    def get_games(self, team_id):
        """ดึงเกมที่ทีมนี้ลงแข่ง (distinct)"""
        games = self.db.fetchall("""
            SELECT DISTINCT game.game_id, game.game_name, game.game_logo
            FROM player
            JOIN game ON player.game_id = game.game_id
            WHERE player.team_id = %s
        """, (team_id,))
        for g in games:
            g["logo"] = g.get("game_logo")
        return games

    def get_tournaments(self, team_id):
        """ดึง tournaments ที่ทีมนี้เคยลงแข่ง"""
        return self.db.fetchall("""
            SELECT DISTINCT t.tournament_id, t.name, t.date, t.location, t.prize_pool,
                            g.game_name, g.game_logo
            FROM `match` m
            JOIN tournament t ON m.tournament_id = t.tournament_id
            LEFT JOIN game g ON t.game_id = g.game_id
            WHERE m.team1_id = %s OR m.team2_id = %s
            ORDER BY t.date DESC
        """, (team_id, team_id))

    def update_tournament(self, team_id, tournament_id):
        """Assign ทีมเข้า tournament"""
        val = tournament_id if tournament_id else None
        self.db.execute(
            "UPDATE team SET tournament_id = %s WHERE team_id = %s",
            (val, team_id)
        )

    def count(self):
        row = self.db.fetchone("SELECT COUNT(*) AS total FROM team")
        return row["total"]

    # ------------------------------------------------------------------
    #  Write (Admin)
    # ------------------------------------------------------------------

    def delete(self, team_id):
        self.db.execute("DELETE FROM team WHERE team_id = %s", (team_id,))