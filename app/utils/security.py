import secrets
import argon2

pwd_hasher = argon2.PasswordHasher()


def generate_salt(n: int) -> bytes:
    """Generate a random salt.
    Args:
        n (int): Length of salt in bytes
    Returns:
        bytes: Random salt
    """
    return secrets.token_bytes(n)


def generate_key(n: int) -> str:
    """Generate a random key.
    Args:
        n (int): Length of key in bytes
    Returns:
        str: Random key
    """
    return secrets.token_urlsafe(n)


def hash_password(password: str, salt: bytes) -> str:
    """Hash password.
    Args:
        password (str): Password to hash
        salt (bytes): Salt to use
    Returns:
        str: Hashed password
    """
    return pwd_hasher.hash(password, salt=salt)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password.
    Args:
        password (str): Password to verify
        hashed_password (str): Hashed password
    Returns:
        bool: `True` if password is correct, `False` otherwise
    """
    try:
        pwd_hasher.verify(hashed_password, password)
        return True
    except argon2.exceptions.VerifyMismatchError:
        return False
