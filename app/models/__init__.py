from typing import Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    """Response class for API responses.

    Attributes:
        message (str): Response message
        data (Optional[T]): Response data
        code (int):
            Response code, default to `0`.
            - `0`: Success
            - `1`: Invalid request
            - `2`: Permission denied
            - `3`: Resource not found
            - `4`: Resource already exists
            - `5`: Internal server error
            - `6`: Session expired
            - `7`: Compatibility issue

    Example:
        1. Success response with empty data
        ```
        from app.utils.response import Response
        response = Response("Success")
        ```

        2. Success response with data
        ```
        from app.utils.response import Response
        response = Response("Success", data={"key": "value"})
        ```

        3. Error response
        ```
        from app.utils.response import Response
        response = Response("Error", code=1)
        ```
    """

    message: str
    data: Optional[T] = None
    code: int = 0

    def __init__(self, message: str, data: Optional[T] = None, code: int = 0):
        super().__init__(message=message, data=data, code=code)
