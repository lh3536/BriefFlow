"""Inspect retrieval and its metrics: python -m backend.retrieval --mode mock."""
import argparse
import json
import logging
import os

from backend.retrieval.service import get_items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("mock", "database", "web"), default="mock")
    parser.add_argument("--db-path", help="Optional SQLite file path")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    os.environ["BRIEFFLOW_RETRIEVAL_MODE"] = args.mode
    if args.db_path:
        os.environ["BRIEFFLOW_DB_PATH"] = args.db_path
    print(json.dumps(get_items({}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
