class TrustSQLError(Exception):
    """A safe, user-facing error. Never include raw upstream errors or SQL here."""

    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)
