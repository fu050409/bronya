from datetime import datetime
from typing import Optional, Self
from pydantic import BaseModel, field_validator, model_validator
from surrealdb import RecordID

from app import utils
from app.db import AsyncWsSurrealConnection
from app.models.session import Session


class Profile(BaseModel):
    """Represents user profile data transfer object."""

    avatar: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    github: Optional[str] = None


class Account(BaseModel, arbitrary_types_allowed=True):
    """Represents user account database model."""

    id: Optional[RecordID]
    username: str
    password: str
    email: Optional[str]
    profile: Profile
    rating: int
    credit_score: int
    is_admin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    async def save_on(self, db: AsyncWsSurrealConnection) -> Optional["Account"]:
        """Save account to database.
        Args:
            db (AsyncWsSurrealConnection): Database connection
        Returns:
            Optional[Account]: Saved account or None if failed
        """
        self.updated_at = datetime.now()

        if self.id:
            account = await db.upsert(self.id, self.model_dump(exclude={"id"}))
        else:
            account = await db.create("account", self.model_dump(exclude={"id"}))

        assert isinstance(account, Optional[dict])
        return None if not account else Account(**account)

    async def delete_on(self, db: AsyncWsSurrealConnection) -> Optional["Account"]:
        """Delete account from database.
        Args:
            db (AsyncWsSurrealConnection): Database connection
        Returns:
            Optional[Account]: Deleted account or None if failed
        """
        if not self.id:
            return None

        account = await db.delete(self.id)
        assert isinstance(account, Optional[dict])
        return None if not account else Account(**account)

    @classmethod
    async def get_by_id(
        cls, db: AsyncWsSurrealConnection, id: RecordID
    ) -> Optional["Account"]:
        """Get account by ID.
        Args:
            db (AsyncWsSurrealConnection): Database connection
            id (RecordID): Account ID
        Returns:
            Optional[Account]: Account or None if not found
        """
        account = await db.select(id)
        assert isinstance(account, Optional[dict])
        return None if not account else Account(**account)

    @classmethod
    async def get_by_identity(
        cls, db: AsyncWsSurrealConnection, identity: str
    ) -> Optional["Account"]:
        """Get account by username or email.
        Args:
            db (AsyncWsSurrealConnection): Database connection
            identity (str): Username or email
        Returns:
            Optional[Account]: Account or None if not found
        """
        account = await db.query(
            "SELECT * FROM account WHERE username = $identity \
                OR email = $identity",
            {
                "identity": identity,
            },
        )
        return Account(**account[0]) if len(account) == 1 else None

    @classmethod
    async def get_by_username(
        cls, db: AsyncWsSurrealConnection, username: str
    ) -> Optional["Account"]:
        """
        Retrieve an account by username.

        Args:
            db (AsyncWsSurrealConnection): The database connection.
            username (str): The username of the account.

        Returns:
            Optional[Account]: The account object if found, otherwise None.
        """
        query = "SELECT * FROM account WHERE username = $username LIMIT 1"
        result = await db.query(query, {"username": username})

        if not result:
            return None

        return Account(**result[0])


class Register(BaseModel):
    """Represents user registration data transfer object.

    Attributes:
        username: Unique identifier for the account (3-20 alphanumeric chars)
        password: Plain text password (will be hashed before storage)
        phone: Optional verified phone number in E.164 format
        email: Optional email address for account recovery
        device_id: Device ID for session management
    """

    username: str
    password: str
    phone: Optional[str] = None
    email: Optional[str] = None
    device_id: str

    @model_validator(mode="after")
    def validate_phone_email(self) -> Self:
        """Validate optional phone and email fields.
        Raises:
            ValueError: If both phone and email are missing
            ValueError: If both phone and email are provided
        Returns:
            Self: Validated registration DTO
        """
        if self.phone is None and self.email is None:
            raise ValueError("At least one of phone or email must be provided.")
        elif self.phone is not None and self.email is not None:
            raise ValueError("Only one of phone or email can be provided.")
        return self

    async def has_conflict_on(self, db: AsyncWsSurrealConnection) -> bool:
        """Check if account with the same username or email already exists.
        Args:
            db (AsyncWsSurrealConnection): Database connection
        Returns:
            bool: True if account with the same username or email exists, False otherwise
        """
        accounts = await db.query(
            "SELECT * FROM account WHERE username = $username \
            OR email = $email OR phone = $phone",
            {
                "username": self.username,
                "email": self.email,
                "phone": self.phone,
            },
        )
        return len(accounts) > 0

    @field_validator("phone")
    def validate_phone(cls, value: str) -> str:
        """Validate phone number format.
        Args:
            value (str): Phone number to validate
        Raises:
            ValueError: If phone number is not in E.164 format
        Returns:
            str: Validated phone number
        """
        if not value.startswith("+"):
            raise ValueError("Phone number must be in E.164 format.")
        return value

    @field_validator("email")
    def validate_email(cls, value: str) -> str:
        """Validate email address format.
        Args:
            value (str): Email address to validate
        Raises:
            ValueError: If email address is not valid
        Returns:
            str: Validated email address
        """
        if not utils.is_valid_email(value):
            raise ValueError("Email address is not valid.")
        return value

    @field_validator("username")
    def validate_username(cls, value: str) -> str:
        """Validate username length and format.
        Args:
            value (str): Username to validate
        Raises:
            ValueError: If username is not between 3 and 20 characters
            ValueError: If username contains non-alphanumeric characters
        Returns:
            str: Validated username
        """
        if not 3 <= len(value) <= 20:
            raise ValueError("Username must be between 3 and 20 characters.")
        if not value.isalnum():
            raise ValueError("Username must contain only alphanumeric characters.")
        return value

    @field_validator("password")
    def validate_password(cls, value: str) -> str:
        """Validate password length.
        Args:
            value (str): Password to validate
        Raises:
            ValueError: If password is less than 8 characters
        Returns:
            str: Validated password
        """
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters.")
        elif len(value) > 32:
            raise ValueError("Password must be at most 32 characters.")

        return value

    def into_account(self) -> Account:
        """Convert registration DTO to Account entity with secure defaults.

        Performs:
        - Password hashing with Argon2id and random salt
        - Profile initialization with empty fields
        - Default values for ratings and account status

        Returns:
            Account: Initialized account entity ready for database storage
        """
        password = utils.hash_password(self.password, salt=utils.generate_salt(16))
        time_now = datetime.now()
        return Account(
            id=None,
            username=self.username,
            password=password,
            email=self.email,
            profile=Profile(),
            rating=0,
            credit_score=60,
            is_admin=False,
            is_active=True,
            created_at=time_now,
            updated_at=time_now,
        )


class Login(BaseModel):
    """Represents user login data transfer object.
    Attributes:
        identity: Unique identifier for the account (username or email)
        password: Plain text password (will be hashed before storage)
        device_id: Device ID for session management
    """

    identity: str
    password: str
    device_id: str

    @field_validator("identity")
    def validate_identity(cls, value: str) -> str:
        """Validate identity format.
        Args:
            value (str): Identity to validate
        Raises:
            ValueError: If identity is not valid
        Returns:
            str: Validated identity
        """
        if not utils.is_valid_email(value) and not value.isalnum():
            raise ValueError("Identity must be a valid email or username.")

        return value


class Credentials(BaseModel):
    """Represents user credentials data transfer object.
    Attributes:
        user_id (str): User ID
        username (str): Username
        token (str): Session token
        device_id (str): Device ID
    """

    user_id: str
    username: str
    token: str
    device_id: str

    async def is_valid_on(self, db: AsyncWsSurrealConnection) -> bool:
        """Validate credentials.
        Args:
            db (AsyncWsSurrealConnection): Database connection
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        session = await Session.get_by_id(db, RecordID("session", self.device_id))
        if session is None or session.id is None:
            return False
        return session.account.id == self.user_id and session.is_valid_token(self.token)
