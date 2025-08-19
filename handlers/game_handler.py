import json
import os
import random
from telebot import types
from utils.constants import (
    WORD_BONUS_PER_LETTER, DISABLED_PREFIX, DISABLED_TAG, REVEAL_ON_SKIP,
    WRONG_WORD_DEDUCT, AUDIO_BRASS, AUDIO_FAIL, AUDIO_LEVELUP, AUDIO_AHERO,
    GIF_CATEGORY_WIN, GIF_GAME_OVER
)
from utils.helpers import spin_wheel, mask_str, sanitize_category, send_audio_if_exists, send_animation_if_exists
from utils.state import (
    get_state, is_category_completed, all_categories_completed,
    get_solved_indices, mark_solved, total_in_category
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUESTIONS_PATH = os.path.join(BASE_DIR, "data", "questions.json")

with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

def show_categories(bot, message):
    user_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    buttons = []
    for category in QUESTIONS.keys():
        if is_category_completed(user_id, category, QUESTIONS):
            buttons.append(types.KeyboardButton(f"{DISABLED_PREFIX}{category}{DISABLED_TAG}"))
        else:
            buttons.append(types.KeyboardButton(category))
    if buttons:
        markup.add(*buttons)
    bot.send_message(message.chat.id, "Оберіть категорію:", reply_markup=markup)

def start_game(bot, message):
    st = get_state(message.chat.id)
    st["in_round"] = False
    st["round"] = None
    show_categories(bot, message)

def launch_round(bot, message, category):
    user_id = message.chat.id
    st = get_state(user_id)
    solved = get_solved_indices(user_id, category)
    total = total_in_category(QUESTIONS, category)
    all_idx = set(range(total))
    remaining = list(all_idx - solved)
    if not remaining:
        bot.send_message(message.chat.id, "У цій категорії всі слова вже відгадані.")
        return show_categories(bot, message)
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
    bot.send_message(
        message.chat.id,
        f"Категорія: {category}\nПідказка: {hint}\n\n{mask_str(round_state['mask'])}\n\n"
        f"Бали за слово: {round_state['score']}\nЗагалом: {st['total_score']}\n\n"
        f"Введи літеру або слово:"
    )

def handle_category_selection(bot, message):
    raw = message.text or ""
    category = sanitize_category(raw)
    user_id = message.chat.id
    if category not in QUESTIONS:
        bot.send_message(message.chat.id, "Невірна категорія. Оберіть зі списку.")
        return show_categories(bot, message)
    if is_category_completed(user_id, category, QUESTIONS):
        bot.send_message(message.chat.id, "Ця категорія вже завершена. Оберіть іншу.")
        return show_categories(bot, message)
    return launch_round(bot, message, category)

def process_guess(bot, message):
    user_id = message.chat.id
    st = get_state(user_id)
    if not st["in_round"] or not st["round"]:
        return show_categories(bot, message)

    r = st["round"]
    guess_up = ((message.text or "").strip()).upper()
    if not guess_up:
        bot.send_message(message.chat.id, "Введи літеру або слово.")
        return

    if len(guess_up) > 1:
        if guess_up == r["word"]:
            unopened = [i for i, ch in enumerate(r["mask"]) if ch == "_"]
            if unopened:
                gained = WORD_BONUS_PER_LETTER * len(unopened)
                r["score"] += gained
                st["total_score"] += gained
                bot.send_message(message.chat.id, f"💎 Бонус! Ти відкрив одразу все слово і отримав {gained} балів")
            bot.send_message(message.chat.id, f"🎉 Вітаю! Ти відгадав слово: {r['word']}\nТвої фінальні бали: {st['total_score']}")
            send_audio_if_exists(bot, message.chat.id, AUDIO_LEVELUP)
            mark_solved(user_id, r["category"], r["word_index"])
            st["in_round"] = False
            st["round"] = None
            if is_category_completed(user_id, r["category"], QUESTIONS):
                send_animation_if_exists(bot, message.chat.id, GIF_CATEGORY_WIN, caption=f"✅ Категорію «{r['category']}» завершено!")
                if all_categories_completed(user_id, QUESTIONS) and st.get("mistakes", 0) == 0:
                    send_audio_if_exists(bot, message.chat.id, AUDIO_AHERO)
            return show_categories(bot, message)
        else:
            st["mistakes"] += 1
            st["total_score"] -= WRONG_WORD_DEDUCT
            send_audio_if_exists(bot, message.chat.id, AUDIO_BRASS)
            if st["total_score"] <= 0:
                send_audio_if_exists(bot, message.chat.id, AUDIO_FAIL)
                send_animation_if_exists(bot, message.chat.id, GIF_GAME_OVER, caption="💀 Поразка!")
            bot.send_message(message.chat.id, "❌ Спроба невдала. Продовжуй відгадувати.")
            bot.send_message(message.chat.id, f"{mask_str(r['mask'])}\n\nБали за слово: {r['score']}\nЗагалом: {st['total_score']}\n\nВведи літеру або слово:")
            return

    if not guess_up.isalpha() or len(guess_up) != 1:
        bot.send_message(message.chat.id, "Введи одну літеру або ціле слово.")
        bot.send_message(message.chat.id, f"{mask_str(r['mask'])}\n\nБали за слово: {r['score']}\nЗагалом: {st['total_score']}\n\nВведи літеру або слово:")
        return

    if guess_up in r["guessed"]:
        bot.send_message(message.chat.id, "Ця літера вже була. Обери іншу.")
        bot.send_message(message.chat.id, f"{mask_str(r['mask'])}\n\nБали за слово: {r['score']}\nЗагалом: {st['total_score']}\n\nВведи літеру або слово:")
        return

    bot.send_message(message.chat.id, "🎡 Барабан крутиться...")
    sector, value = spin_wheel()

    if value == 0:
        if REVEAL_ON_SKIP and guess_up in r["word"]:
            r["guessed"].add(guess_up)
            for i, ch in enumerate(r["word"]):
                if ch == guess_up:
                    r["mask"][i] = guess_up
            bot.send_message(message.chat.id, f"⏭️ Пропуск ходу. Літеру {guess_up} відкрито без балів.")
            if "_" not in r["mask"]:
                bot.send_message(message.chat.id, f"🎉 Вітаю! Ти відгадав слово: {r['word']}\nТвої фінальні бали: {st['total_score']}")
                send_audio_if_exists(bot, message.chat.id, AUDIO_LEVELUP)
                mark_solved(user_id, r["category"], r["word_index"])
                st["in_round"] = False
                st["round"] = None
                if is_category_completed(user_id, r["category"], QUESTIONS):
                    send_animation_if_exists(bot, message.chat.id, GIF_CATEGORY_WIN, caption=f"✅ Категорію «{r['category']}» завершено!")
                    if all_categories_completed(user_id, QUESTIONS) and st.get("mistakes", 0) == 0:
                        send_audio_if_exists(bot, message.chat.id, AUDIO_AHERO)
                return show_categories(bot, message)
        else:
            bot.send_message(message.chat.id, "⏭️ Пропуск ходу. Літеру не зараховано.")
        bot.send_message(message.chat.id, f"{mask_str(r['mask'])}\n\nБали за слово: {r['score']}\nЗагалом: {st['total_score']}\n\nВведи літеру або слово:")
        return

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
        bot.send_message(message.chat.id, f"✅ Є літера {guess_up}! +{gained} балів")
    else:
        st["mistakes"] += 1
        st["total_score"] -= value
        send_audio_if_exists(bot, message.chat.id, AUDIO_BRASS)
        bot.send_message(message.chat.id, f"❌ Літери {guess_up} немає у слові. -{value} балів")
        if st["total_score"] <= 0:
            send_audio_if_exists(bot, message.chat.id, AUDIO_FAIL)
            send_animation_if_exists(bot, message.chat.id, GIF_GAME_OVER, caption="💀 Поразка!")

    if "_" not in r["mask"]:
        bot.send_message(message.chat.id, f"🎉 Вітаю! Ти відгадав слово: {r['word']}\nТвої фінальні бали: {st['total_score']}")
        send_audio_if_exists(bot, message.chat.id, AUDIO_LEVELUP)
        mark_solved(user_id, r["category"], r["word_index"])
        st["in_round"] = False
        st["round"] = None
        if is_category_completed(user_id, r["category"], QUESTIONS):
            send_animation_if_exists(bot, message.chat.id, GIF_CATEGORY_WIN, caption=f"✅ Категорію «{r['category']}» завершено!")
            if all_categories_completed(user_id, QUESTIONS) and st.get("mistakes", 0) == 0:
                send_audio_if_exists(bot, message.chat.id, AUDIO_AHERO)
        return show_categories(bot, message)

    bot.send_message(message.chat.id, f"{mask_str(r['mask'])}\n\nБали за слово: {r['score']}\nЗагалом: {st['total_score']}\n\nВведи наступну літеру або спробуй слово:")

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
            show_categories(bot, message)
