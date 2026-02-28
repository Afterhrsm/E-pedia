from .base_model import BaseModel


class User(BaseModel):
    """จัดการข้อมูล user และ authentication"""

    # ------------------------------------------------------------------
    #  Auth
    # ------------------------------------------------------------------

    def login(self, username, password):
        """ตรวจสอบ username + password คืน user dict หรือ None"""
        return self.db.fetchone(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (username, password)
        )

    def get_by_username(self, username):
        """ดึงข้อมูล user จาก username"""
        return self.db.fetchone(
            "SELECT * FROM users WHERE username = %s",
            (username,)
        )

    def get_id(self, username):
        """คืนแค่ user_id จาก username"""
        row = self.db.fetchone(
            "SELECT user_id FROM users WHERE username = %s",
            (username,)
        )
        return row["user_id"] if row else None

    # ------------------------------------------------------------------
    #  Admin
    # ------------------------------------------------------------------

    def get_all(self):
        return self.db.fetchall("SELECT * FROM users")

    def count(self):
        row = self.db.fetchone("SELECT COUNT(*) AS total FROM users")
        return row["total"]

    def delete(self, user_id):
        self.db.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
