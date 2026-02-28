from .base_model import BaseModel


class Tournament(BaseModel):
    """จัดการข้อมูลทัวร์นาเมนต์และ matches"""

    # ------------------------------------------------------------------
    #  Read — Tournament
    # ------------------------------------------------------------------

    def get_all(self):
        return self.db.fetchall("""
            SELECT tournament.*, game.game_name
            FROM tournament
            LEFT JOIN game ON tournament.game_id = game.game_id
        """)

    def get_by_id(self, tournament_id):
        return self.db.fetchone("""
            SELECT tournament.*, game.game_name
            FROM tournament
            LEFT JOIN game ON tournament.game_id = game.game_id
            WHERE tournament.tournament_id = %s
        """, (tournament_id,))

    def count(self):
        row = self.db.fetchone("SELECT COUNT(*) AS total FROM tournament")
        return row["total"]

    # ------------------------------------------------------------------
    #  Read — Matches
    # ------------------------------------------------------------------

    def get_matches(self, tournament_id):
        """ดึง matches ใน tournament พร้อม team info"""
        matches = self.db.fetchall("""
            SELECT m.*,
                   t1.team_name  AS team1_name,  t1.short_name AS team1_short_name, t1.logo AS team1_logo,
                   t2.team_name  AS team2_name,  t2.short_name AS team2_short_name, t2.logo AS team2_logo
            FROM `match` m
            LEFT JOIN team t1 ON m.team1_id = t1.team_id
            LEFT JOIN team t2 ON m.team2_id = t2.team_id
            WHERE m.tournament_id = %s
            ORDER BY m.match_date, m.match_time
        """, (tournament_id,))
        for m in matches:
            m["team1_logo"] = self.to_base64(m.get("team1_logo"))
            m["team2_logo"] = self.to_base64(m.get("team2_logo"))
        return matches

    def get_all_matches(self):
        """ดึง matches ทั้งหมดทุก tournament — สำหรับ admin"""
        return self.db.fetchall("""
            SELECT m.*,
                   t1.team_name AS team1_name,
                   t2.team_name AS team2_name,
                   t.name       AS tournament_name
            FROM `match` m
            LEFT JOIN team       t1 ON m.team1_id       = t1.team_id
            LEFT JOIN team       t2 ON m.team2_id       = t2.team_id
            LEFT JOIN tournament t  ON m.tournament_id  = t.tournament_id
            ORDER BY m.match_date DESC, m.match_time DESC
        """)

    def get_tournament_id_of_match(self, match_id):
        row = self.db.fetchone(
            "SELECT tournament_id FROM `match` WHERE match_id = %s",
            (match_id,)
        )
        return row["tournament_id"] if row else 1

    # ------------------------------------------------------------------
    #  Read — Votes
    # ------------------------------------------------------------------

    def get_user_votes(self, user_id):
        """คืน dict: { match_id: team_id }"""
        rows = self.db.fetchall(
            "SELECT match_id, team_id FROM vote WHERE user_id = %s",
            (user_id,)
        )
        return {r["match_id"]: r["team_id"] for r in rows}

    def get_vote_counts(self):
        """คืน dict: { match_id: { team_id: count } }"""
        rows = self.db.fetchall("""
            SELECT match_id, team_id, COUNT(*) AS cnt
            FROM vote
            GROUP BY match_id, team_id
        """)
        counts = {}
        for r in rows:
            counts.setdefault(r["match_id"], {})[r["team_id"]] = r["cnt"]
        return counts

    # ------------------------------------------------------------------
    #  Write — Vote
    # ------------------------------------------------------------------

    def cast_vote(self, match_id, user_id, team_id):
        """โหวตหรืออัปเดตโหวต (upsert)"""
        self.db.execute("""
            INSERT INTO vote (match_id, user_id, team_id)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE team_id = %s
        """, (match_id, user_id, team_id, team_id))

    # ------------------------------------------------------------------
    #  Write — Score (Admin)
    # ------------------------------------------------------------------

    def update_score(self, match_id, team1_score, team2_score):
        """อัปเดตสกอร์ทั้งคู่พร้อมกัน"""
        self.db.execute("""
            UPDATE `match`
            SET team1_score = %s, team2_score = %s
            WHERE match_id = %s
        """, (team1_score, team2_score, match_id))

    # ------------------------------------------------------------------
    #  Write — Delete (Admin)
    # ------------------------------------------------------------------

    def delete(self, tournament_id):
        self.db.execute(
            "DELETE FROM tournament WHERE tournament_id = %s",
            (tournament_id,)
        )