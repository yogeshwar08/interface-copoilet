import time
import uuid


def uuid7():
    """
    Pure-Python UUIDv7-compatible implementation.

    UUIDv7 contains the Unix timestamp in milliseconds
    followed by random bits.
    """

    timestamp_ms = int(time.time() * 1000)

    random_uuid = uuid.uuid4()

    random_int = random_uuid.int

    uuid_int = (
        (timestamp_ms & ((1 << 48) - 1)) << 80
    )

    uuid_int |= (
        0x7 << 76
    )

    uuid_int |= (
        (random_int >> 62) & 0xFFF
    ) << 64

    uuid_int |= (
        0x2 << 62
    )

    uuid_int |= (
        random_int & ((1 << 62) - 1)
    )

    return uuid.UUID(int=uuid_int)