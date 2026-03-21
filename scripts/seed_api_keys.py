import argparse

from pipeline.queue.database import get_session
from pipeline.queue.repository import TaskRepository


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed or revoke API keys")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--internal", action="store_true", help="Create internal API key")
    group.add_argument("--external", metavar="USER_ID", help="Create external API key")
    group.add_argument("--revoke", metavar="USER_ID", help="Revoke API key for user")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    with get_session() as session:
        repo = TaskRepository(session)
        if args.internal:
            raw_key = repo.create_api_key(user_id="internal", role="internal")
            print(raw_key)
            return
        if args.external:
            raw_key = repo.create_api_key(user_id=args.external, role="external")
            print(raw_key)
            return
        if args.revoke:
            repo.revoke_api_key(user_id=args.revoke)
            print("revoked")
            return


if __name__ == "__main__":
    main()
