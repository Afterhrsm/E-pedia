import mysql.connector


class Database:
    """จัดการ connection กับ MySQL database"""

    _config = {
        "host":     "localhost",
        "user":     "root",
        "password": "",
        "database": "esport_db",
    }

    def __init__(self):
        self._conn   = mysql.connector.connect(**self._config)
        self._cursor = self._conn.cursor(dictionary=True)

    # ------------------------------------------------------------------
    #  Query helpers
    # ------------------------------------------------------------------

    def fetchone(self, sql, params=()):
        self._cursor.execute(sql, params)
        return self._cursor.fetchone()

    def fetchall(self, sql, params=()):
        self._cursor.execute(sql, params)
        return self._cursor.fetchall()

    def execute(self, sql, params=()):
        self._cursor.execute(sql, params)
        self._conn.commit()

    # ------------------------------------------------------------------
    #  Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        self._cursor.close()
        self._conn.close()

    # รองรับ `with Database() as db:`
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
