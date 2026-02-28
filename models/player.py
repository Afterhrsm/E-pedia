from .base_model import BaseModel


class Player(BaseModel):
    """จัดการข้อมูลผู้เล่น"""

    # ------------------------------------------------------------------
    #  Read
    # ------------------------------------------------------------------

    def get_all(self):
        players = self.db.fetchall("""
            SELECT player_id, nickname, team_id, image,
                   (SELECT team_name FROM team WHERE team.team_id = player.team_id) AS team_name
            FROM player
        """)
        for p in players:
            p["image"] = self.to_base64(p.get("image"))
        return players

    def get_by_id(self, player_id):
        player = self.db.fetchone("""
            SELECT player.*, team.team_name, game.game_name
            FROM player
            LEFT JOIN team ON player.team_id = team.team_id
            LEFT JOIN game ON player.game_id = game.game_id
            WHERE player.player_id = %s
        """, (player_id,))
        if player:
            player["image"] = self.to_base64(player.get("image"))
            player["cover"] = player.get("cover_image")
        return player

    def get_fav_players(self, user_id):
        """ดึง players ที่ user ถูกใจ"""
        players = self.db.fetchall("""
            SELECT p.player_id, p.nickname, p.role, p.image, t.team_name
            FROM favorite f
            JOIN player p ON f.item_id = p.player_id
            LEFT JOIN team t ON p.team_id = t.team_id
            WHERE f.user_id = %s AND f.item_type = 'player'
        """, (user_id,))
        for p in players:
            p["image"] = self.to_base64(p.get("image"))
        return players

    def count(self):
        row = self.db.fetchone("SELECT COUNT(*) AS total FROM player")
        return row["total"]

    def get_all_with_team(self):
        """สำหรับ admin panel"""
        return self.db.fetchall("""
            SELECT player.*, team.team_name, game.game_name
            FROM player
            LEFT JOIN team ON player.team_id = team.team_id
            LEFT JOIN game ON player.game_id = game.game_id
        """)

    # ------------------------------------------------------------------
    #  Write (Admin)
    # ------------------------------------------------------------------

    def delete(self, player_id):
        self.db.execute("DELETE FROM player WHERE player_id = %s", (player_id,))