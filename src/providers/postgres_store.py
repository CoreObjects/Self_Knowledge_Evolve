"""PostgresRelationalStore — RelationalStore implementation backed by src/db/postgres.py."""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from contextlib import contextmanager
from typing import Any, Generator

from semcore.providers.base import RelationalStore
import src.db.postgres as pg

import logging

log = logging.getLogger(__name__)


class PostgresRelationalStore(RelationalStore):
    def fetchone(self, sql: str, params: tuple | dict | None = None) -> dict[str, Any] | None:
        return pg.fetchone(sql, params or ())

    def fetchall(self, sql: str, params: tuple | dict | None = None) -> list[dict[str, Any]]:
        return pg.fetchall(sql, params or ())

    def execute(self, sql: str, params: tuple | dict | None = None) -> None:
        pg.execute(sql, params or ())

    @contextmanager
    def transaction(self) -> Generator[Any, None, None]:
        with pg.get_conn() as conn:
            with conn.cursor() as cur:
                yield cur