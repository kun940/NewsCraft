def _error_body(code: int, message: str) -> dict:
    """和 ResponseBase(code, message, data) 对齐的统一错误体"""
    return {"code": code, "message": message, "data": None}