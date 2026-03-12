import argparse
import asyncio

from config import logger
from dependencies.auth import generate_owner_reset_link


async def cmd_get_reset_owner(args):
    link = await generate_owner_reset_link(args.email)
    print("\nPassword reset link:\n")
    print(link)
    print("\nOpen it in browser to set a new password.")


def main():
    parser = argparse.ArgumentParser(
        description="Portal backend maintenance CLI"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    reset_parser = subparsers.add_parser(
        "get-reset-link",
        help=(
            "Generate password reset link for any user "
            "(primarily intended for owner recovery)"
        ),
    )

    reset_parser.add_argument(
        "email",
        help="User email (normally owner email)"
    )

    args = parser.parse_args()

    try:
        if args.command == "get-reset-link":
            asyncio.run(cmd_get_reset_owner(args))
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    main()

# docker exec -it portal_backend python cli.py get-reset-link owner@example.com
