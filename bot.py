import telebot
import os
import logging
import time

# Настройка логирования для отладки
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация бота
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))
GROUP_ID = os.getenv('GROUP_ID')  # ID группы, куда будут пересылаться сообщения

# Словарь для хранения связи между ID пересланных сообщений и оригинальными чатами
message_map = {}

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Добро пожаловать! Напишите мне, и я перешлю ваше сообщение в группу.")
    logging.info(f"Start command received from {message.chat.id}")

# Команда для получения ID чата
@bot.message_handler(commands=['getid'])
def send_chat_id(message):
    bot.reply_to(message, f"ID чата: {message.chat.id}")
    logging.info(f"Chat ID requested: {message.chat.id}")

# Обработчик всех сообщений от пользователей (не из группы)
@bot.message_handler(content_types=['text', 'photo', 'document', 'sticker', 'video', 'audio'])
def handle_user_message(message):
    if GROUP_ID is None:
        bot.send_message(message.chat.id, "Ошибка: GROUP_ID не задан. Установите переменную окружения GROUP_ID в настройках сервера.")
        logging.error("GROUP_ID is not set")
        return
    if str(message.chat.id) != GROUP_ID:  # Проверяем, что сообщение не из группы
        try:
            # Пересылаем сообщение в группу
            forwarded_message = bot.forward_message(GROUP_ID, message.chat.id, message.message_id)
            logging.info(f"Message forwarded from {message.chat.id} to group {GROUP_ID}, forwarded message ID: {forwarded_message.message_id}")
            # Сохраняем связь в словаре
            message_map[forwarded_message.message_id] = {
                'original_chat_id': message.chat.id,
                'original_message_id': message.message_id,
                'timestamp': time.time()
            }
            logging.debug(f"Stored in message_map: {forwarded_message.message_id} -> {message_map[forwarded_message.message_id]}")
        except Exception as e:
            logging.error(f"Error forwarding message: {e}")
            bot.send_message(message.chat.id, f"Ошибка при пересылке сообщения: {e}")

# Обработчик всех текстовых сообщений в группе
@bot.message_handler(content_types=['text'], func=lambda message: str(message.chat.id) == GROUP_ID)
def handle_group_reply(message):
    if GROUP_ID is None:
        logging.error("GROUP_ID is not set in group reply handler")
        return
    logging.debug(f"Received message in group {GROUP_ID}: {message.text}, reply_to_message: {message.reply_to_message.message_id if message.reply_to_message else None}")
    if message.reply_to_message and hasattr(message.reply_to_message, 'forward_from') or hasattr(message.reply_to_message, 'forward_from_chat'):
        try:
            # Получаем данные о пересланном сообщении
            chat_data = message_map.get(message.reply_to_message.message_id)
            logging.debug(f"Looking for chat_data for message ID {message.reply_to_message.message_id}: {chat_data}")
            if chat_data and 'original_chat_id' in chat_data:
                original_chat_id = chat_data['original_chat_id']
                # Отправляем ответ пользователю
                sent_message = bot.send_message(original_chat_id, message.text)
                logging.info(f"Reply sent to user {original_chat_id} from group {GROUP_ID}, reply message ID: {sent_message.message_id}")
            else:
                logging.warning(f"No chat data found for message ID {message.reply_to_message.message_id}")
                bot.send_message(GROUP_ID, f"Не удалось найти информацию о пересланном сообщении. Убедитесь, что вы отвечаете на сообщение, пересланное ботом.")
        except Exception as e:
            logging.error(f"Error handling group reply: {e}")
            bot.send_message(GROUP_ID, f"Ошибка при отправке ответа: {e}")
    else:
        logging.debug(f"Message is not a reply or not forwarded: {message.reply_to_message}")

# Очистка старых записей в message_map для экономии памяти
def clean_message_map():
    # Удаляем записи старше 1 часа (3600 секунд)
    current_time = time.time()
    expired_keys = [key for key, value in message_map.items() if current_time - value.get('timestamp', 0) > 3600]
    for key in expired_keys:
        del message_map[key]
    logging.debug(f"Cleaned message_map, remaining entries: {len(message_map)}")

# Запуск бота с обработкой ошибок
while True:
    try:
        logging.info("Starting bot polling...")
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        logging.error(f"Polling error: {e}")
        time.sleep(5)  # Ждём 5 секунд перед повторной попыткой
        clean_message_map()  # Очищаем message_map при перезапуске
