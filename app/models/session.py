from datetime import datetime, timedelta
from typing import Optional, Self
from pydantic import BaseModel
from surrealdb import RecordID

from app import utils
from app.db import AsyncWsSurrealConnection

import jwt
import secrets


class JwtPayload(BaseModel):
    """Represents JWT payload.
    Attributes:
        account_id (str): Account ID
        random_part (str): Random part of token
        device_id (str): Device ID
        iat (int): Issued at
        exp (int): Expiration time
    """

    account_id: str
    random_part: str
    device_id: str
    iat: int
    exp: int


class Session(BaseModel, arbitrary_types_allowed=True):
    """Represents session.
    Attributes:
        id (RecordID): Session ID
        account (RecordID): Account ID
        key (str): Session key
        token (str): Session token
        created_at (datetime): Created at
        updated_at (datetime): Updated at
    """

    id: RecordID
    account: RecordID
    key: str
    token: str
    created_at: datetime
    updated_at: datetime

    async def save_on(self, db: AsyncWsSurrealConnection) -> Optional["Session"]:
        """Save session to database.
        Args:
            db (AsyncWsSurrealConnection): Database connection
        Returns:
            Optional[Session]: Saved session or None if failed
        """
        self.updated_at = datetime.now()
        session = await db.upsert(self.id, self.model_dump())
        assert isinstance(session, Optional[dict])
        return None if not session else Session(**session)

    @classmethod
    async def get_by_id(
        cls, db: AsyncWsSurrealConnection, id: RecordID
    ) -> Optional["Session"]:
        """Get session by ID.
        Args:
            db (AsyncWsSurrealConnection): Database connection
            id (RecordID): Session ID
        Returns:
            Optional[Session]: Session or None if not found
        """
        session = await db.select(id)
        assert isinstance(session, Optional[dict])
        return None if not session else Session(**session)

    def is_valid_token(self, token: str) -> bool:
        """Validate session token.
        Args:
            token (str): Session token
        Returns:
            bool: True if token is valid, False otherwise
        """
        try:
            jwt.decode(token, self.key, algorithms=["HS256"])
            return True
        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False

    async def delete_on(self, db: AsyncWsSurrealConnection) -> Optional["Session"]:
        """Delete session from database.
        Args:
            db (AsyncWsSurrealConnection): Database connection
        Returns:
            bool: True if deleted, False otherwise
        """
        session = await db.delete(self.id)
        assert isinstance(session, Optional[dict])
        return None if not session else Session(**session)

    @classmethod
    def generate(cls, account: RecordID, device_id: str) -> "Session":
        """Generate session.
        Args:
            account (RecordID): Account ID
        Returns:
            Session: Generated session
        """
        time_now = datetime.now()
        key = utils.generate_key(32)
        return Session(
            id=RecordID("session", device_id),
            account=account,
            key=key,
            token=cls.generate_token(account, device_id, key),
            created_at=time_now,
            updated_at=time_now,
        )

    @staticmethod
    def generate_token(account: RecordID, device_id: str, key: str) -> str:
        """Generate session token.
        Args:
            account (RecordID): Account ID
        Returns:
            str: Generated session token
        """
        payload = JwtPayload(
            account_id=account.id,
            random_part=secrets.token_hex(8),
            device_id=device_id,
            iat=int(datetime.now().timestamp()),
            exp=int(datetime.now().timestamp() + timedelta(days=30).total_seconds()),
        )
        return jwt.encode(payload.model_dump(), key, algorithm="HS256")

    def refresh(self) -> Self:
        """Refresh session token.
        Returns:
            Session: Refreshed session
        """
        self.token = self.generate_token(self.account, self.id.id, self.key)
        return self

    async def refresh_and_save_on(self, db: AsyncWsSurrealConnection) -> Self:
        """Refresh session and save to database.
        Args:
            db (AsyncWsSurrealConnection): Database connection
        Returns:
            Session: Refreshed session
        """
        self.refresh()
        await self.save_on(db)
        return self
