from __future__ import annotations

import json
from collections import deque
from typing import TYPE_CHECKING, Dict, List, Optional, Protocol, Tuple

import aiosqlite

from ...settings import get_settings

if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from .registry import Job


class JobStore(Protocol):
    async def save_job(self, job: Job) -> None: ...

    async def get_job(self, job_id: str) -> Optional[dict]: ...

    async def list_jobs(self) -> List[dict]: ...

    async def delete_job(self, job_id: str) -> None: ...

    async def save_event(self, job_id: str, event_id: int, envelope: dict) -> None: ...

    async def events_since(self, job_id: str, event_id: int) -> List[dict]: ...

    async def save_idempotency(self, key: str, job_id: str, ts: float) -> None: ...

    async def get_idempotent(self, key: str, now: float, ttl: float) -> Optional[str]: ...

    async def close(self) -> None: ...


class MemoryJobStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.jobs: Dict[str, dict] = {}
        self.events: Dict[str, deque] = {}
        self.idempotency: Dict[str, Tuple[str, float]] = {}
        self.buffer_size = settings.SSE_BUFFER_SIZE

    async def save_job(self, job: Job) -> None:
        self.jobs[job.id] = {
            "id": job.id,
            "status": job.status.value,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "result": job.result,
        }

    async def get_job(self, job_id: str) -> Optional[dict]:
        job = self.jobs.get(job_id)
        if job:
            return dict(job)
        return None

    async def list_jobs(self) -> List[dict]:
        return list(self.jobs.values())

    async def delete_job(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)
        self.events.pop(job_id, None)

    async def save_event(self, job_id: str, event_id: int, envelope: dict) -> None:
        buf = self.events.setdefault(job_id, deque(maxlen=self.buffer_size))
        buf.append(envelope)

    async def events_since(self, job_id: str, event_id: int) -> List[dict]:
        buf = self.events.get(job_id, deque())
        return [env for env in list(buf) if env.get("id", 0) > event_id]

    async def save_idempotency(self, key: str, job_id: str, ts: float) -> None:
        self.idempotency[key] = (job_id, ts)

    async def get_idempotent(self, key: str, now: float, ttl: float) -> Optional[str]:
        info = self.idempotency.get(key)
        if info and now - info[1] < ttl:
            return info[0]
        return None

    async def close(self) -> None:
        return None


class SQLiteJobStore:
    def __init__(self, db: aiosqlite.Connection) -> None:
        settings = get_settings()
        self.db = db
        self.buffer_size = settings.SSE_BUFFER_SIZE

    @classmethod
    async def create(cls, path: str) -> "SQLiteJobStore":
        db = await aiosqlite.connect(path)
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT,
                created_at REAL,
                updated_at REAL,
                result TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                job_id TEXT,
                id INTEGER,
                envelope TEXT,
                PRIMARY KEY(job_id, id)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS idempotency (
                key TEXT PRIMARY KEY,
                job_id TEXT,
                created_at REAL
            )
            """
        )
        await db.commit()
        return cls(db)

    async def save_job(self, job: Job) -> None:
        await self.db.execute(
            """
            INSERT INTO jobs(id, status, created_at, updated_at, result)
            VALUES(?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at,
                result=excluded.result
            """,
            (
                job.id,
                job.status.value,
                job.created_at,
                job.updated_at,
                json.dumps(job.result, separators=(",",":")) if job.result is not None else None,
            ),
        )
        await self.db.commit()

    async def get_job(self, job_id: str) -> Optional[dict]:
        async with self.db.execute(
            "SELECT id, status, created_at, updated_at, result FROM jobs WHERE id=?",
            (job_id,),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        result = json.loads(row[4]) if row[4] else None
        return {
            "id": row[0],
            "status": row[1],
            "created_at": row[2],
            "updated_at": row[3],
            "result": result,
        }

    async def list_jobs(self) -> List[dict]:
        async with self.db.execute(
            "SELECT id, status, created_at, updated_at, result FROM jobs ORDER BY created_at DESC"
        ) as cur:
            rows = await cur.fetchall()
        res = []
        for row in rows:
            res.append(
                {
                    "id": row[0],
                    "status": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                    "result": json.loads(row[4]) if row[4] else None,
                }
            )
        return res

    async def delete_job(self, job_id: str) -> None:
        await self.db.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        await self.db.execute("DELETE FROM events WHERE job_id=?", (job_id,))
        await self.db.commit()

    async def save_event(self, job_id: str, event_id: int, envelope: dict) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO events(job_id, id, envelope) VALUES(?,?,?)",
            (job_id, event_id, json.dumps(envelope, separators=(",",":"))),
        )
        cutoff = event_id - self.buffer_size
        if cutoff > 0:
            await self.db.execute(
                "DELETE FROM events WHERE job_id=? AND id<=?", (job_id, cutoff)
            )
        await self.db.commit()

    async def events_since(self, job_id: str, event_id: int) -> List[dict]:
        async with self.db.execute(
            "SELECT envelope FROM events WHERE job_id=? AND id>? ORDER BY id",
            (job_id, event_id),
        ) as cur:
            rows = await cur.fetchall()
        return [json.loads(row[0]) for row in rows]

    async def save_idempotency(self, key: str, job_id: str, ts: float) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO idempotency(key, job_id, created_at) VALUES(?,?,?)",
            (key, job_id, ts),
        )
        await self.db.commit()

    async def get_idempotent(self, key: str, now: float, ttl: float) -> Optional[str]:
        async with self.db.execute(
            "SELECT job_id, created_at FROM idempotency WHERE key=?", (key,)
        ) as cur:
            row = await cur.fetchone()
        if row and now - row[1] < ttl:
            return row[0]
        return None

    async def close(self) -> None:
        await self.db.close()
