from surrealdb.connections.async_ws import AsyncWsSurrealConnection
from surrealdb import AsyncSurreal

db: AsyncWsSurrealConnection = AsyncSurreal("ws://127.0.0.1:5070")  # type: ignore we use async ws connection


async def init_surrealdb():
    """Initialize surrealdb."""
    await db.signin(
        {
            "username": "root",
            "password": "root",
        }
    )
    await db.use("test", "test")

    # Define event for delete sessions when account is deleted
    await db.query(
        "DEFINE EVENT OVERWRITE delete_sessions ON TABLE account WHEN $event = 'DELETE' THEN (\
            DELETE session WHERE account = $before.id\
        )"
    )
