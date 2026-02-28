from .base_model import BaseModel


class Favorite(BaseModel):
    """จัดการ favorites ของ user (team / player / game)"""

    VALID_TYPES = {"team", "player", "game"}

    # ------------------------------------------------------------------
    #  Read
    # ------------------------------------------------------------------

    def get_all(self, user_id):
        """คืน dict of sets: { 'team': {1,2}, 'player': {3}, 'game': {1} }"""
        rows = self.db.fetchall(
            "SELECT item_type, item_id FROM favorite WHERE user_id = %s",
            (user_id,)
        )
        favs = {t: set() for t in self.VALID_TYPES}
        for row in rows:
            favs[row["item_type"]].add(row["item_id"])
        return favs

    def is_fav(self, user_id, item_type, item_id):
        """ตรวจว่า user ถูกใจ item นี้อยู่หรือเปล่า"""
        row = self.db.fetchone(
            "SELECT favorite_id FROM favorite WHERE user_id = %s AND item_type = %s AND item_id = %s",
            (user_id, item_type, item_id)
        )
        return row

    # ------------------------------------------------------------------
    #  Write
    # ------------------------------------------------------------------

    def toggle(self, user_id, item_type, item_id):
        """toggle favorite — ถ้ามีอยู่แล้วให้ลบ ถ้าไม่มีให้เพิ่ม"""
        if item_type not in self.VALID_TYPES:
            return

        existing = self.is_fav(user_id, item_type, item_id)
        if existing:
            self.db.execute(
                "DELETE FROM favorite WHERE favorite_id = %s",
                (existing["favorite_id"],)
            )
        else:
            self.db.execute(
                "INSERT INTO favorite (user_id, item_type, item_id) VALUES (%s, %s, %s)",
                (user_id, item_type, item_id)
            )
