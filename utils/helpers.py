import os
import time
import json
import random
from tqdm import tqdm
from telebot import types
from .constants import WHEEL, DISABLED_PREFIX, DISABLED_TAG, QUESTIONS_PATH, ROUND_STATUS_TEMPLATE, BASE_DIR


def resolve_path(rel_path):
    return os.path.join(BASE_DIR, rel_path)

def load_questions(file_path=None):
    if file_path is None:
        file_path = QUESTIONS_PATH
    try:
        with open(resolve_path(file_path), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def spin_wheel():
    for _ in tqdm(range(30), desc="🎡 Обертання барабана"):
        time.sleep(0.05)
    return random.choice(WHEEL)

def mask_str(chars):
    return " ".join(chars)

def sanitize_category(text):
    return (text or "").replace(DISABLED_PREFIX, "").replace(DISABLED_TAG, "").strip()

def send_audio_if_exists(bot, chat_id, rel_path):
    path = resolve_path(rel_path)
    try:
        with open(path, "rb") as f:
            bot.send_audio(chat_id, f)
    except FileNotFoundError:
        pass

def send_animation_if_exists(bot, chat_id, rel_path, caption=None):
    path = resolve_path(rel_path)
    try:
        with open(path, "rb") as f:
            bot.send_animation(chat_id, f, caption=caption)
    except FileNotFoundError:
        pass

def create_category_keyboard(user_id, questions):
    from .state import is_category_completed
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    buttons = []
    for category in questions.keys():
        if is_category_completed(user_id, category, questions):
            buttons.append(types.KeyboardButton(f"{DISABLED_PREFIX}{category}{DISABLED_TAG}"))
        else:
            buttons.append(types.KeyboardButton(category))
    if buttons:
        markup.add(*buttons)
    return markup

def get_random_question(category, solved_indices, questions):
    total = len(questions.get(category, []))
    all_indices = set(range(total))
    remaining = list(all_indices - solved_indices)
    if not remaining:
        return None
    word_index = random.choice(remaining)
    return questions[category][word_index], word_index

def format_round_start_message(category, hint, masked_word, word_score, total_score):
    return (f"Категорія: {category}\n"
            f"Підказка: {hint}\n\n"
            f"{masked_word}\n\n"
            f"Бали за слово: {word_score}\n"
            f"Загалом: {total_score}\n\n"
            f"Введи літеру або слово:")

def calculate_word_bonus(word, mask):
    unopened = [i for i, ch in enumerate(mask) if ch == "_"]
    return len(unopened) * 1000

def update_mask(word, guess, current_mask):
    new_mask = current_mask.copy()
    count = 0
    for i, ch in enumerate(word):
        if ch == guess:
            new_mask[i] = guess
            count += 1
    return new_mask, count

def is_round_complete(mask):
    return "_" not in mask

def get_round_status_text(round_state, total_score):
    return ROUND_STATUS_TEMPLATE.format(
        mask=mask_str(round_state['mask']),
        score=round_state['score'],
        total_score=total_score
    )

def try_complete_round(bot, user_id, state, round_state):
    from .state import mark_solved, is_category_completed, all_categories_completed
    from .constants import AUDIO_LEVELUP, GIF_CATEGORY_WIN, AUDIO_AHERO, WIN_MESSAGE, CATEGORY_WIN_MESSAGE
    if "_" not in round_state["mask"]:
        bot.send_message(user_id, WIN_MESSAGE.format(
            word=round_state['word'],
            score=state['total_score']
        ))
        send_audio_if_exists(bot, user_id, AUDIO_LEVELUP)
        mark_solved(user_id, round_state["category"], round_state["word_index"])
        state["in_round"] = False
        state["round"] = None
        if is_category_completed(user_id, round_state["category"]):
            send_animation_if_exists(
                bot,
                user_id,
                GIF_CATEGORY_WIN,
                caption=CATEGORY_WIN_MESSAGE.format(category=round_state['category'])
            )
            if all_categories_completed(user_id) and state.get("mistakes", 0) == 0:
                send_audio_if_exists(bot, user_id, AUDIO_AHERO)
        return True
    return False

def handle_wrong_word(bot, user_id, state):
    from .constants import AUDIO_BRASS, AUDIO_FAIL, GIF_GAME_OVER, WRONG_WORD_DEDUCT, GAME_OVER_MESSAGE
    state["mistakes"] += 1
    state["total_score"] -= WRONG_WORD_DEDUCT
    send_audio_if_exists(bot, user_id, AUDIO_BRASS)
    if state["total_score"] <= 0:
        send_audio_if_exists(bot, user_id, AUDIO_FAIL)
        send_animation_if_exists(bot, user_id, GIF_GAME_OVER, caption=GAME_OVER_MESSAGE)