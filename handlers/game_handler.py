import random
from utils.constants import (
    WORD_BONUS_PER_LETTER, DISABLED_PREFIX, DISABLED_TAG, REVEAL_ON_SKIP,
    AUDIO_BRASS, AUDIO_FAIL, AUDIO_LEVELUP, AUDIO_AHERO,
    GIF_CATEGORY_WIN, GIF_GAME_OVER, QUESTIONS_PATH,
    CATEGORY_SELECTION_TEXT, SKIP_TURN_MESSAGE, CORRECT_LETTER_MESSAGE,
    WRONG_LETTER_MESSAGE, ALREADY_GUESSED_MESSAGE, INVALID_INPUT_MESSAGE,
    CATEGORY_COMPLETE_MESSAGE, GAME_OVER_MESSAGE, SPINNING_WHEEL_MESSAGE,
    WORD_GUESSED_MESSAGE, BONUS_MESSAGE, WRONG_WORD_MESSAGE, COMPLETED_CATEGORY_MESSAGE,
    INVALID_CATEGORY_MESSAGE, SKIP_TURN_NO_REVEAL_MESSAGE, CATEGORY_WIN_MESSAGE
)
from utils.helpers import (
    spin_wheel,  sanitize_category, send_audio_if_exists,
    send_animation_if_exists, get_round_status_text, try_complete_round,
    handle_wrong_word, load_questions
)
from utils.state import (
    get_state, is_category_completed, all_categories_completed,
    get_solved_indices, mark_solved, total_in_category
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
        f"Категорія: {category}\nПідказка: {hint}\n\n{status_text}"
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
        bot.send_message(message.chat.id, INVALID_INPUT_MESSAGE)
        return None
    if len(guess_up) > 1:
        if guess_up == r["word"]:
            unopened = [i for i, ch in enumerate(r["mask"]) if ch == "_"]
            if unopened:
                gained = WORD_BONUS_PER_LETTER * len(unopened)
                r["score"] += gained
                st["total_score"] += gained
                bot.send_message(message.chat.id, BONUS_MESSAGE.format(gained=gained))
            bot.send_message(message.chat.id, WORD_GUESSED_MESSAGE.format(word=r['word'], score=st['total_score']))
            send_audio_if_exists(bot, message.chat.id, AUDIO_LEVELUP)
            mark_solved(user_id, r["category"], r["word_index"])
            st["in_round"] = False
            st["round"] = None
            if is_category_completed(user_id, r["category"], QUESTIONS):
                send_animation_if_exists(bot, message.chat.id, GIF_CATEGORY_WIN, caption=CATEGORY_WIN_MESSAGE.format(category=r['category']))
                if all_categories_completed(user_id, QUESTIONS) and st.get("mistakes", 0) == 0:
                    send_audio_if_exists(bot, message.chat.id, AUDIO_AHERO)
            return show_categories(bot, message.chat.id)
        else:
            handle_wrong_word(bot, user_id, st)
            bot.send_message(message.chat.id, WRONG_WORD_MESSAGE)
            status_text = get_round_status_text(r, st['total_score'])
            bot.send_message(message.chat.id, status_text)
            return None
    if not guess_up.isalpha() or len(guess_up) != 1:
        bot.send_message(message.chat.id, INVALID_INPUT_MESSAGE)
        status_text = get_round_status_text(r, st['total_score'])
        bot.send_message(message.chat.id, status_text)
        return None
    if guess_up in r["guessed"]:
        bot.send_message(message.chat.id, ALREADY_GUESSED_MESSAGE)
        status_text = get_round_status_text(r, st['total_score'])
        bot.send_message(message.chat.id, status_text)
        return None
    bot.send_message(message.chat.id, SPINNING_WHEEL_MESSAGE)
    sector, value = spin_wheel()
    if value == 0:
        if REVEAL_ON_SKIP and guess_up in r["word"]:
            r["guessed"].add(guess_up)
            for i, ch in enumerate(r["word"]):
                if ch == guess_up:
                    r["mask"][i] = guess_up
            bot.send_message(message.chat.id, SKIP_TURN_MESSAGE.format(letter=guess_up))
            if try_complete_round(bot, user_id, st, r):
                return show_categories(bot, message.chat.id)
        else:
            bot.send_message(message.chat.id, SKIP_TURN_NO_REVEAL_MESSAGE)
        status_text = get_round_status_text(r, st['total_score'])
        bot.send_message(message.chat.id, status_text)
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
        bot.send_message(message.chat.id, CORRECT_LETTER_MESSAGE.format(letter=guess_up, gained=gained))
    else:
        st["mistakes"] += 1
        st["total_score"] -= value
        send_audio_if_exists(bot, message.chat.id, AUDIO_BRASS)
        bot.send_message(message.chat.id, WRONG_LETTER_MESSAGE.format(letter=guess_up, value=value))
        if st["total_score"] <= 0:
            send_audio_if_exists(bot, message.chat.id, AUDIO_FAIL)
            send_animation_if_exists(bot, message.chat.id, GIF_GAME_OVER, caption=GAME_OVER_MESSAGE)
    if try_complete_round(bot, user_id, st, r):
        return show_categories(bot, message.chat.id)
    status_text = get_round_status_text(r, st['total_score'])
    bot.send_message(message.chat.id, status_text)
    return None


def register_handlers(bot):
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