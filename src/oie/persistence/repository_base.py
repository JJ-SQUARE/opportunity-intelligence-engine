from __future__ import annotations

import sqlite3

from oie.persistence.context import PersistenceContext


class RepositoryBase:
    def __init__(
        self,
        db_path: str = "data/oie.db",
        persistence: PersistenceContext | None = None,
    ) -> None:
        self.db_path = db_path
        self.persistence = persistence or PersistenceContext.from_sqlite_path(db_path)

    def connection(self) -> sqlite3.Connection:
        return self.persistence.connection()

