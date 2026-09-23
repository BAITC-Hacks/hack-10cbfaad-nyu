import argparse
import json
from pathlib import Path

from .config import get_settings
from .database import build_engine, build_session_factory, initialize_database
from .service import upsert_product


def main() -> None:
    parser = argparse.ArgumentParser(description="Load a product JSON fixture")
    parser.add_argument(
        "path",
        nargs="?",
        default="fixtures/product_515291_raw.json",
    )
    arguments = parser.parse_args()
    fixture_path = Path(arguments.path)
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    settings = get_settings()
    engine = build_engine(settings.product_database_url)
    initialize_database(engine)
    factory = build_session_factory(engine)
    try:
        with factory() as session:
            product = upsert_product(
                session,
                payload,
                sync_id="development-fixture",
                is_detail=True,
            )
            session.commit()
            print(f"Loaded product {product.id}: {product.name}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
