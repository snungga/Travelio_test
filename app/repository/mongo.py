"""MongoDB repository (optional).

Selected when REPO_BACKEND=mongo. Uses `motor` (async). Importing this module is
deferred in `dependencies.py` so the in-memory default never needs motor running.
"""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient

from app.models import ClassificationRecord


class MongoRepository:
    def __init__(self, uri: str, db_name: str, collection: str) -> None:
        self._client = AsyncIOMotorClient(uri)
        self._collection = self._client[db_name][collection]

    async def save(self, record: ClassificationRecord) -> str:
        # mode="json" turns enums/datetimes into Mongo-friendly primitives.
        result = await self._collection.insert_one(record.model_dump(mode="json"))
        return str(result.inserted_id)

    async def list(self, limit: int = 100) -> list[ClassificationRecord]:
        cursor = self._collection.find().sort("timestamp", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [ClassificationRecord.model_validate(doc) for doc in docs]
