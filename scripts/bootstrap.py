"""Prepare a fresh demo database, sample accounts, and qualification model.

Run with ``python -m scripts.bootstrap`` before starting the API. Safe to run
again: schema creation and the starter-data seed are idempotent.
"""
from pathlib import Path

from app.config import MODEL_PATH
from app.database import engine
from app.models import Base
from scripts.seed import main as seed_demo_data


def main() -> None:
    Base.metadata.create_all(engine)
    seed_demo_data()

    model_path = Path(MODEL_PATH)
    if not model_path.exists():
        from app.ml.train import generate_synthetic_data, train

        print("Training the demo qualification model...")
        train(generate_synthetic_data(), model_path)
    else:
        print(f"Qualification model already available at {model_path}.")


if __name__ == "__main__":
    main()
