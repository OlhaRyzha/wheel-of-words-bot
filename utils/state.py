import json
import os
from typing import Dict, Any

USER_STATES: Dict[int, Dict[str, Any]] = {}
STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "user_state.json",
)


def _default_state() -> Dict[str, Any]:
    return {
        "total_score": 0,
        "mistakes": 0,
        "in_round": False,
        "round": None,
        "solved": {},
    }


def get_state(user_id: int) -> Dict[str, Any]:
    if user_id not in USER_STATES:
        USER_STATES[user_id] = _default_state()
    return USER_STATES[user_id]


def reset_state(user_id: int) -> Dict[str, Any]:
    USER_STATES[user_id] = _default_state()
    return USER_STATES[user_id]


def _ensure_set(st: Dict[str, Any], category: str) -> set:
    s = st["solved"].get(category)
    if isinstance(s, set):
        return s
    if s is None:
        s = set()
    else:
        try:
            s = set(s)
        except TypeError:
            s = set()
    st["solved"][category] = s
    return s


def total_in_category(questions: dict, category: str) -> int:
    arr = questions.get(category, [])
    total = 0
    for item in arr:
        try:
            w = (item.get("word") or "").strip()
            if w:
                total += 1
        except AttributeError:
            continue
    return total


def get_solved_indices(user_id: int, category: str) -> set:
    st = get_state(user_id)
    return _ensure_set(st, category)


def mark_solved(user_id: int, category: str, index: int) -> None:
    st = get_state(user_id)
    s = _ensure_set(st, category)
    try:
        s.add(int(index))
    except (ValueError, TypeError):
        pass


def is_category_completed(user_id: int, category: str, questions: dict) -> bool:
    solved = get_solved_indices(user_id, category)
    total = total_in_category(questions, category)
    return 0 < total <= len(solved)


def all_categories_completed(user_id: int, questions: dict) -> bool:
    for category in questions.keys():
        if not is_category_completed(user_id, category, questions):
            return False
    return True


def save_user_progress() -> bool:
    try:
        dump: Dict[str, Any] = {}
        for uid, st in USER_STATES.items():
            solved_serializable = {
                cat: sorted(list(indices)) for cat, indices in st["solved"].items()
            }
            out = dict(st)
            out["solved"] = solved_serializable
            dump[str(uid)] = out
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(dump, f, ensure_ascii=False, indent=2)
        return True
    except (OSError, ValueError, TypeError):
        return False


def load_user_progress() -> bool:
    if not os.path.exists(STATE_FILE):
        return False
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for uid_str, st in data.items():
            uid = int(uid_str)
            st.setdefault("total_score", 0)
            st.setdefault("mistakes", 0)
            st.setdefault("in_round", False)
            st.setdefault("round", None)
            st.setdefault("solved", {})
            solved = {cat: set(indices) for cat, indices in st["solved"].items()}
            st["solved"] = solved
            USER_STATES[uid] = st
        return True
    except (OSError, ValueError, json.JSONDecodeError, TypeError):
        return False
