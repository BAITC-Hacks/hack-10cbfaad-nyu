import argparse
import json

from .config import get_settings
from .database import build_engine, build_session_factory, initialize_database
from .ekt_client import EktClient
from .schemas import SyncRequest
from .service import sync_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize the ekt.kz catalog")
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Import list data without requesting every product detail",
    )
    parser.add_argument("--max-pages", type=int, default=None)
    arguments = parser.parse_args()

    settings = get_settings()
    engine = build_engine(settings.product_database_url)
    initialize_database(engine)
    factory = build_session_factory(engine)
    client = EktClient(
        base_url=settings.ekt_api_base_url,
        username=settings.ekt_api_username,
        password=settings.ekt_api_password,
        timeout=settings.ekt_http_timeout_seconds,
    )
    try:
        with factory() as session:
            result = sync_catalog(
                session,
                client,
                SyncRequest(
                    enrich_details=not arguments.no_enrich,
                    max_pages=arguments.max_pages,
                ),
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        client.close()
        engine.dispose()


if __name__ == "__main__":
    main()
