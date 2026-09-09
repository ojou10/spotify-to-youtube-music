class ConnectorError(Exception):
    def __init__(self, code: str, summary: str, *, retryable: bool = False):
        super().__init__(summary)
        self.code = code
        self.summary = summary
        self.retryable = retryable


class AuthenticationRequired(ConnectorError):
    def __init__(self, summary: str = "authentication is required"):
        super().__init__("authentication_required", summary)


class ValidationFailure(ConnectorError):
    def __init__(self, summary: str):
        super().__init__("validation_error", summary)
