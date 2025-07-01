class Response:
    def __init__(self, status_code: int = 200, text: str = "ok") -> None:
        self.status_code = status_code
        self.text = text


def post(url: str, data=None, timeout: int | None = None) -> Response:  # noqa: D401
    """Stub requests.post that returns a dummy response."""
    return Response()
