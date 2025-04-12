import re


def is_valid_email(email: str) -> bool:
    """Check if email is valid.
    Args:
        email (str): Email to check
    Returns:
        bool: True if email is valid, False otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None
