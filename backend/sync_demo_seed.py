from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete

from backend.core.config import settings
from backend.db import SessionLocal
from backend.seed import SEED_MODELS, _prepare_payload, _read_json, _sync_postgres_sequences


def sync_demo_seed() -> None:
    manifest_path = settings.seed_data_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest = _read_json(manifest_path)
    import_order = manifest.get("import_order", [])

    with SessionLocal() as db:
        for filename in reversed(import_order):
            dataset_name = Path(filename).stem
            model = SEED_MODELS.get(dataset_name)
            if model is None:
                continue
            db.execute(delete(model))
        db.commit()

        for filename in import_order:
            dataset_name = Path(filename).stem
            model = SEED_MODELS.get(dataset_name)
            if model is None:
                continue

            payload_path = settings.seed_data_dir / filename
            if not payload_path.exists():
                continue

            for row in _read_json(payload_path):
                db.add(model(**_prepare_payload(dataset_name, row)))

        db.commit()
        _sync_postgres_sequences(db)


if __name__ == "__main__":
    sync_demo_seed()
    print("Demo seed synchronized successfully.")
