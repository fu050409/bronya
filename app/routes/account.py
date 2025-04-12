from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from surrealdb import RecordID
from app import utils
from app.db import db
from app.models import Response
from app.models.account import Account, Credentials, Login, Profile, Register
from app.models.session import Session


router = APIRouter()


class UserToken(BaseModel):
    """Represents user token data transfer object.
    Attributes:
        user_id (str): User ID
        username (str): Username
        token (str): Session token
    """

    user_id: str
    username: str
    token: str


@router.post("/create", tags=["account"])
async def register(data: Register) -> Response[Optional[UserToken]]:
    """Register account."""
    if await data.has_conflict_on(db):
        return Response("Account already exists.", code=4)

    # TODO: Check if phone or email is verified
    # TODO: Send verification code to phone or email
    account: Optional[Account] = await data.into_account().save_on(db)
    if account is None or account.id is None:
        return Response("Failed to create account.", code=5)
    session = await Session.generate(account.id, data.device_id).save_on(db)
    if session is None or session.id is None:
        return Response("Failed to create session.", code=5)

    return Response(
        "Account created successfully.",
        data=UserToken(
            user_id=account.id.id,
            username=account.username,
            token=session.token,
        ),
    )


@router.post("/login", tags=["account"])
async def login(data: Login) -> Response[Optional[UserToken]]:
    """Login account."""
    account = await Account.get_by_identity(db, data.identity)
    if account is None or account.id is None:
        return Response("Account not found.", code=4)
    if not utils.verify_password(data.password, account.password):
        return Response("Invalid password.", code=2)

    # TODO: Support 2FA

    exist_session = await Session.get_by_id(db, RecordID("session", data.device_id))
    if exist_session is not None:
        session = await exist_session.refresh_and_save_on(db)
    else:
        session = await Session.generate(account.id, data.device_id).save_on(db)

    if session is None or session.id is None:
        return Response("Failed to create or update session.", code=5)

    return Response(
        "Logged in successfully.",
        data=UserToken(
            user_id=account.id.id,
            username=account.username,
            token=session.token,
        ),
    )


@router.delete("/delete", tags=["account"])
async def delete_account(credentials: Credentials) -> Response[None]:
    """Delete account."""
    if not await credentials.is_valid_on(db):
        return Response("Invalid credentials.", code=2)
    account = await Account.get_by_id(db, RecordID("account", credentials.user_id))
    if account is None or account.id is None:
        return Response("Account not found.", code=4)
    removed_account = await account.delete_on(db)
    if removed_account is None or removed_account.id is None:
        return Response("Failed to delete account.", code=5)
    return Response("Account deleted successfully.")


class UpdateProfile(BaseModel):
    """Represents user profile update data transfer object.
    Attributes:
        credentials (Credentials): User credentials
        profile (Profile): User profile
    """

    credentials: Credentials
    profile: Profile


@router.put("/profile/update", tags=["account"])
async def update_profile(data: UpdateProfile) -> Response[Optional[Profile]]:
    """Update user profile."""
    credentials, profile = data.credentials, data.profile
    if not await credentials.is_valid_on(db):
        return Response("Invalid credentials.", code=2)
    account = await Account.get_by_id(db, RecordID("account", credentials.user_id))
    if account is None or account.id is None:
        return Response("Account not found.", code=4)
    account.profile = profile
    updated_account = await account.save_on(db)
    if updated_account is None or updated_account.id is None:
        return Response("Failed to update profile.", code=5)
    return Response("Profile updated successfully.", data=updated_account.profile)


@router.post("/logout", tags=["account"])
async def logout(credentials: Credentials) -> Response[None]:
    """Logout account."""
    if not await credentials.is_valid_on(db):
        return Response("Invalid credentials.", code=2)
    session = await Session.get_by_id(db, RecordID("session", credentials.device_id))
    if session is None or session.id is None:
        return Response("Session not found.", code=4)
    removed_session = await session.delete_on(db)
    if removed_session is None or removed_session.id is None:
        return Response("Failed to logout.", code=5)
    return Response("Logged out successfully.")
