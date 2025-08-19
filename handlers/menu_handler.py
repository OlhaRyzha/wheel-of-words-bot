from telebot import types

from handlers.game_handler import start_game
from utils.constants import HELP_TEXT


def register_handlers(bot):
    @bot.message_handler(commands=['start'])
    def start(message):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        play_btn = types.KeyboardButton("🎮 Грати в Поле Чудес")
        help_btn= types.KeyboardButton("Правила")
        kb.add(play_btn, help_btn)
        name = " ".join(filter(None, [message.from_user.first_name, message.from_user.last_name]))
        bot.send_message(
            message.chat.id,
            f"{name}, вітаю у грі «Поле Чудес»! 🎉\nНатисни кнопку нижче, щоб почати гру.",
            reply_markup=kb
        )

    @bot.message_handler(commands=['help'])
    def cmd_help(message):
        bot.send_message(message.chat.id, HELP_TEXT)

    @bot.message_handler(func=lambda m: m.text == "Правила")
    def btn_help(message):
        bot.send_message(message.chat.id, HELP_TEXT)

    @bot.message_handler(func=lambda m: m.text == "🎮 Грати в Поле Чудес")
    def play_btn(message):
        start_game(bot, message)
