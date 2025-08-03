import telebot
import os

# Инициализация бота
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))
GROUP_ID = os.getenv('GROUP_ID')  # ID группы, куда будут пересылаться сообщения

# Обработчик всех текстовых сообщений от пользователей (не из группы)
@bot.message_handler(content_types=['text', 'photo', 'document', 'sticker', 'video', 'audio'])
def handle_user_message(message):
    if message.chat.id != int(GROUP_ID):  # Проверяем, что сообщение не из группы
        # Пересылаем сообщение в группу
        forwarded_message = bot.forward_message(GROUP_ID, message.chat.id, message.message_id)
        # Сохраняем связь между оригинальным сообщением и пересланным
        bot.register_next_step_handler_by_chat_id(
            GROUP_ID,
            lambda reply: handle_group_reply(reply, message.chat.id, message.message_id)
        )

# Обработчик ответов в группе
def handle_group_reply(reply, original_chat_id, original_message_id):
    if reply.chat.id == int(GROUP_ID) and reply.reply_to_message:  # Проверяем, что это ответ в группе
        # Проверяем, что ответ на пересланное сообщение
        if reply.reply_to_message.forward_from or reply.reply_to_message.forward_from_chat:
            # Отправляем ответ пользователю
            bot.send_message(original_chat_id, reply.text)

# Запуск бота
@bot.message_handler(commands=['getid'])
def send_chat_id(message):
    bot.reply_to(message, f"ID чата: {message.chat.id}")
bot.polling(none_stop=True)
