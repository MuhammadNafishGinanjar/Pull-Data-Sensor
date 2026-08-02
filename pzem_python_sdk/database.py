from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient


class PowerReadingRepository:
    def __init__(self, database_name: str, collection_name: str) -> None:
        mongo_uri = os.environ.get("MONGO_URI")
        if not mongo_uri:
            raise RuntimeError(
                "Environment variable MONGO_URI belum diisi. "
                "Isi dengan URI koneksi MongoDB sebelum menjalankan program."
            )

        self.client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
            appname="pzem-power-collector",
        )
        self.client.admin.command("ping")

        self.collection = self.client[database_name][collection_name]
        self.collection.create_index(
            [("machine_id", ASCENDING), ("timestamp", DESCENDING)]
        )

    def save(
        self,
        measurement: dict[str, Any],
        machine_id: str,
        machine_name: str,
        sensor_model: str,
        slave_id: int,
    ) -> str:
        document = {
            "machine_id": machine_id,
            "machine_name": machine_name,
            "sensor_type": "power_meter",
            "sensor_model": sensor_model,
            "slave_id": slave_id,
            "timestamp": datetime.now(timezone.utc),
            **measurement,
        }
        result = self.collection.insert_one(document)
        return str(result.inserted_id)

    def close(self) -> None:
        self.client.close()
