"""Simple in-memory state machine for multi-step conversations."""

_states: dict[int, str] = {}
_data:   dict[int, dict] = {}


def set_state(uid: int, state: str):       _states[uid] = state
def get_state(uid: int) -> str | None:     return _states.get(uid)
def clear_state(uid: int):                 _states.pop(uid, None); _data.pop(uid, None)
def set_data(uid: int, k: str, v):        _data.setdefault(uid, {})[k] = v
def get_data(uid: int, k: str, d=None):   return _data.get(uid, {}).get(k, d)
