"""One error type for the whole API so every failure has the same JSON shape."""


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details=None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details

    def to_response(self):
        body = {"error": {"code": self.code, "message": self.message}}
        if self.details:
            body["error"]["details"] = self.details
        return body, self.status


def not_found(what="Resource"):
    return ApiError(404, "not_found", f"{what} not found")
