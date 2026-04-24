from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4
import hashlib

from opportunity_crawler.shared.db.base import connect_sqlite


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    username: str
    roles: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "username": self.username, "roles": list(self.roles)}


class AuthService:
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self._sessions: dict[str, AuthenticatedUser] = {}

    @staticmethod
    def hash_password(password: str) -> str:
        digest = hashlib.sha256(f"opportunity-crawler:{password}".encode("utf-8")).hexdigest()
        return f"sha256${digest}"

    def authenticate(self, username: str, password: str) -> tuple[str, AuthenticatedUser] | None:
        with connect_sqlite(self.database_path) as connection:
            user_row = connection.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ? AND status = 'active'",
                (username,),
            ).fetchone()
            if user_row is None:
                return None
            if user_row["password_hash"] != self.hash_password(password):
                return None
            roles = tuple(
                row["name"]
                for row in connection.execute(
                    """
                    SELECT r.name
                    FROM roles r
                    JOIN user_roles ur ON ur.role_id = r.id
                    WHERE ur.user_id = ?
                    ORDER BY r.name
                    """,
                    (user_row["id"],),
                ).fetchall()
            )
        token = uuid4().hex
        user = AuthenticatedUser(id=int(user_row["id"]), username=str(user_row["username"]), roles=roles)
        self._sessions[token] = user
        return token, user

    def user_for_token(self, token: str) -> AuthenticatedUser | None:
        return self._sessions.get(token)

