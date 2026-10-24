def user_group(user_id: int) -> str:
    return f"user-{user_id}"


def pc_group(pc_id: int) -> str:
    """클라이언트 연결이 들어가는 그룹."""
    return f"pc-{pc_id}"


def pc_watch_group(pc_id: int) -> str:
    """PC 하나를 보는 브라우저가 들어가는 그룹."""
    return f"pcwatch-{pc_id}"


def room_group(room_id: int) -> str:
    return f"room-{room_id}"


def room_public_group(room_id: int) -> str:
    return f"room-{room_id}-public"
