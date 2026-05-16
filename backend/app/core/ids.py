from uuid import UUID

from uuid6 import uuid7


def new_uuid() -> UUID:
    return uuid7()

