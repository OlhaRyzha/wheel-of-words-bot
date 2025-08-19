user_state = {}

def get_state(user_id):
    if user_id not in user_state:
        user_state[user_id] = {
            "solved": {},
            "in_round": False,
            "round": None,
            "total_score": 0,
            "mistakes": 0
        }
    return user_state[user_id]

def _ensure_set(st, category):
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

def total_in_category(questions, category):
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

def get_solved_indices(user_id, category):
    st = get_state(user_id)
    return _ensure_set(st, category)

def mark_solved(user_id, category, index):
    st = get_state(user_id)
    s = _ensure_set(st, category)
    try:
        s.add(int(index))
    except Exception:
        pass

def is_category_completed(user_id, category, questions):
    st = get_state(user_id)
    solved = _ensure_set(st, category)
    total = total_in_category(questions, category)
    return total > 0 and len(solved) >= total

def all_categories_completed(user_id, questions):
    for category in questions.keys():
        if not is_category_completed(user_id, category, questions):
            return False
    return True
