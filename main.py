import telebot
from handlers import menu_handler, game_handler
from config import TOKEN

bot = telebot.TeleBot(TOKEN)

menu_handler.register_handlers(bot)
game_handler.register_handlers(bot)

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
