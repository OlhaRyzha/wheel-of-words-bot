import random
from utils.constants import (
    WORD_BONUS_PER_LETTER, DISABLED_PREFIX, DISABLED_TAG, REVEAL_ON_SKIP,
    AUDIO_BRASS, AUDIO_FAIL,  GIF_GAME_OVER, QUESTIONS_PATH,
    CATEGORY_SELECTION_TEXT, SKIP_TURN_MESSAGE, CORRECT_LETTER_MESSAGE,
    WRONG_LETTER_MESSAGE, ALREADY_GUESSED_MESSAGE, INVALID_INPUT_MESSAGE,
    CATEGORY_COMPLETE_MESSAGE, GAME_OVER_MESSAGE, SPINNING_WHEEL_MESSAGE,
    BONUS_MESSAGE, WRONG_WORD_MESSAGE, COMPLETED_CATEGORY_MESSAGE,
    INVALID_CATEGORY_MESSAGE, SKIP_TURN_NO_REVEAL_MESSAGE, BTN_SKIP_ROUND,
    CANCELLED_ROUND_MESSAGE, BTN_RESET, RESET_DONE_MESSAGE
)
from utils.helpers import (
    spin_wheel, sanitize_category, send_audio_if_exists,
    send_animation_if_exists, get_round_status_text, try_complete_round,
    handle_wrong_word, load_questions, create_round_keyboard
)
from utils.state import (
    get_state, is_category_completed,
    get_solved_indices,  total_in_category, reset_state, save_user_progress
)

QUESTIONS = load_questions(QUESTIONS_PATH)

def show_categories(bot, chat_id):
    user_id = chat_id
    from utils.helpers import create_category_keyboard
    markup = create_category_keyboard(user_id, QUESTIONS)
    bot.send_message(chat_id, CATEGORY_SELECTION_TEXT, reply_markup=markup)

def start_game(bot, message):
    st = get_state(message.chat.id)
    st["in_round"] = False
    st["round"] = None
    show_categories(bot, message.chat.id)

def launch_round(bot, message, category):

    user_id = message.chat.id
    st = get_state(user_id)
    solved = get_solved_indices(user_id, category)
    total = total_in_category(QUESTIONS, category)
    all_idx = set(range(total))
    remaining = list(all_idx - solved)
    if not remaining:
        bot.send_message(message.chat.id, CATEGORY_COMPLETE_MESSAGE)
        return show_categories(bot, message.chat.id)
    word_index = random.choice(remaining)
    data = QUESTIONS[category][word_index]
    word = (data["word"] or "").upper()
    hint = data["hint"]
    round_state = {
        "category": category,
        "word_index": word_index,
        "word": word,
        "hint": hint,
        "guessed": set(),
        "mask": ["_" for _ in word],
        "score": 0
    }
    st["in_round"] = True
    st["round"] = round_state
    status_text = get_round_status_text(round_state, st['total_score'])
    bot.send_message(
        message.chat.id,
        f"Категорія: {category}\nПідказка: {hint}\n\n{status_text}",
        reply_markup=create_round_keyboard()
    )

    return None


def handle_category_selection(bot, message):
    raw = message.text or ""
    category = sanitize_category(raw)
    user_id = message.chat.id
    if category not in QUESTIONS:
        bot.send_message(message.chat.id, INVALID_CATEGORY_MESSAGE)
        return show_categories(bot, message.chat.id)
    if is_category_completed(user_id, category, QUESTIONS):
        bot.send_message(message.chat.id, COMPLETED_CATEGORY_MESSAGE)
        return show_categories(bot, message.chat.id)
    return launch_round(bot, message, category)

def process_guess(bot, message):
    user_id = message.chat.id
    st = get_state(user_id)
    if not st["in_round"] or not st["round"]:
        return show_categories(bot, message.chat.id)
    r = st["round"]
    guess_up = ((message.text or "").strip()).upper()
    if not guess_up:
        bot.send_message(user_id, INVALID_INPUT_MESSAGE)
        return None
    if len(guess_up) > 1:
        if len(guess_up) > 1:
            if guess_up == r["word"]:
                unopened = [i for i, ch in enumerate(r["mask"]) if ch == "_"]
                if unopened:
                    gained = WORD_BONUS_PER_LETTER * len(unopened)
                    r["score"] += gained
                    st["total_score"] += gained
                    bot.send_message(user_id, BONUS_MESSAGE.format(gained=gained))
                r["mask"] = list(r["word"])
                if try_complete_round(bot, user_id, st, r):
                    return show_categories(bot, user_id)
                status_text = get_round_status_text(r, st['total_score'])
                bot.send_message(user_id, status_text, reply_markup=create_round_keyboard())
                return None
            else:
                handle_wrong_word(bot, user_id, st)
                bot.send_message(user_id, WRONG_WORD_MESSAGE)
                status_text = get_round_status_text(r, st['total_score'])
                bot.send_message(user_id, status_text, reply_markup=create_round_keyboard())
                return None

        else:
            handle_wrong_word(bot, user_id, st)
            bot.send_message(user_id, WRONG_WORD_MESSAGE)
            status_text = get_round_status_text(r, st['total_score'])
            bot.send_message(user_id, status_text, reply_markup=create_round_keyboard())
            return None
    if not guess_up.isalpha() or len(guess_up) != 1:
        bot.send_message(user_id, INVALID_INPUT_MESSAGE)
        status_text = get_round_status_text(r, st['total_score'])
        bot.send_message(user_id, status_text, reply_markup=create_round_keyboard())
        return None
    if guess_up in r["guessed"]:
        bot.send_message(user_id, ALREADY_GUESSED_MESSAGE)
        status_text = get_round_status_text(r, st['total_score'])
        bot.send_message(user_id, status_text, reply_markup=create_round_keyboard())
        return None
    bot.send_message(user_id, SPINNING_WHEEL_MESSAGE)
    sector, value = spin_wheel()
    if value == 0:
        if REVEAL_ON_SKIP and guess_up in r["word"]:
            r["guessed"].add(guess_up)
            for i, ch in enumerate(r["word"]):
                if ch == guess_up:
                    r["mask"][i] = guess_up
            bot.send_message(user_id, SKIP_TURN_MESSAGE.format(letter=guess_up))
            if try_complete_round(bot, user_id, st, r):
                return show_categories(bot,user_id)
        else:
            bot.send_message(user_id, SKIP_TURN_NO_REVEAL_MESSAGE)
        status_text = get_round_status_text(r, st['total_score'])
        bot.send_message(user_id, status_text, reply_markup=create_round_keyboard())
        return None
    r["guessed"].add(guess_up)
    if guess_up in r["word"]:
        count = 0
        for i, ch in enumerate(r["word"]):
            if ch == guess_up:
                r["mask"][i] = guess_up
                count += 1
        gained = value * count
        r["score"] += gained
        st["total_score"] += gained
        bot.send_message(user_id, CORRECT_LETTER_MESSAGE.format(letter=guess_up, gained=gained))
    else:
        st["mistakes"] += 1
        st["total_score"] -= value
        send_audio_if_exists(bot, user_id, AUDIO_BRASS)
        bot.send_message(user_id, WRONG_LETTER_MESSAGE.format(letter=guess_up, value=value))
        if st["total_score"] <= 0:
            send_audio_if_exists(bot, user_id, AUDIO_FAIL)
            send_animation_if_exists(bot, user_id, GIF_GAME_OVER, caption=GAME_OVER_MESSAGE)
    if try_complete_round(bot, user_id, st, r):
        return show_categories(bot, user_id)
    status_text = get_round_status_text(r, st['total_score'])
    bot.send_message(user_id, status_text, reply_markup=create_round_keyboard())
    return None


def register_handlers(bot):
    @bot.message_handler(func=lambda m: m.text == BTN_SKIP_ROUND and get_state(m.chat.id)["in_round"])
    def skip_round(message):
        user_id = message.chat.id
        st = get_state(user_id)
        st["in_round"] = False
        st["round"] = None
        bot.send_message(user_id, CANCELLED_ROUND_MESSAGE)
        show_categories(bot,user_id)

    @bot.message_handler(func=lambda m: m.text == BTN_RESET)
    def reset_game(message):
        user_id = message.chat.id
        reset_state(user_id)
        try:
            save_user_progress()
        except (OSError, ValueError):
            pass
        bot.send_message(user_id, RESET_DONE_MESSAGE)
        show_categories(bot, user_id)

    @bot.message_handler(commands=["start"])
    def cmd_start(message):
        start_game(bot, message)
    @bot.message_handler(func=lambda m: m.text == "🎮 Грати в Поле Чудес")
    def play_btn(message):
        start_game(bot, message)
    @bot.message_handler(func=lambda m: not get_state(m.chat.id)["in_round"] and (m.text and (m.text in QUESTIONS.keys() or m.text.startswith(DISABLED_PREFIX) or m.text.endswith(DISABLED_TAG))))
    def category_buttons(message):
        handle_category_selection(bot, message)
    @bot.message_handler(func=lambda m: get_state(m.chat.id)["in_round"])
    def game_flow(message):
        process_guess(bot, message)
    @bot.message_handler(func=lambda m: True)
    def fallback(message):
        if not get_state(message.chat.id)["in_round"]:
            show_categories(bot, message.chat.id)
