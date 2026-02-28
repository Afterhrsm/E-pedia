import base64


class BaseModel:
    """Base class ที่ทุก model สืบทอด — มี db และ utility methods"""

    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------
    #  Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def to_base64(data):
        """แปลง BLOB / bytes / string → base64 string สำหรับแสดงรูปใน HTML"""
        if not data:
            return None
        if isinstance(data, (bytes, bytearray)):
            return base64.b64encode(data).decode("utf-8")
        if isinstance(data, str):
            return data
        return None
