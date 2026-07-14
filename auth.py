from config import MANAGER_CODE


def is_manager_code(code: str) -> bool:
    return code == MANAGER_CODE


def normalize_code(code: str) -> str:
    return code.strip()