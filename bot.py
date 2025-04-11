from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ParseMode
from config import BOT_TOKEN
from weather import get_weather
import json

# Создаём экземпляр бота с токеном
bot = Bot(token=BOT_TOKEN)

# Создаём диспетчер — он распределяет входящие сообщения
dp = Dispatcher(bot)

# Для простоты будем хранить выбранный город каждого пользователя в глобальном словаре.
# В реальном проекте стоит использовать базу данных или state storage.
user_city = {}
user_city_history = {}


# Обработчик команды /start
@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Напиши название города, чтобы узнать погоду.")


#####################
# Обработчик текстовых сообщений (название города)
#####################
@dp.message_handler()
async def get_weather_info(message: types.Message):
    city = message.text.strip()
    user_city[message.from_user.id] = city

    # Сохраняем город в истории
    if message.from_user.id not in user_city_history:
        user_city_history[message.from_user.id] = []
    user_city_history[message.from_user.id].append(city)

    # Создаём клавиатуру с выбором периода прогноза
    await send_forecast_keyboard(message=message, user_id=message.from_user.id)


#####################
# Обработчик callback-запросов (нажатие на кнопки прогноза)
#####################
@dp.callback_query_handler(lambda call: call.data and call.data.startswith("forecast:"))
async def process_forecast_callback(call: CallbackQuery):
    # Извлекаем количество дней из callback_data, например "forecast:3" → число 3
    _, days_str = call.data.split(":")
    days = int(days_str)

    # Получаем сохраненный город для этого пользователя
    city = user_city.get(call.from_user.id)
    if not city:
        await bot.answer_callback_query(call.id, text="Город не найден. Введи название города снова.")
        return

    # Получаем данные прогноза с помощью функции get_forecast()
    forecast_data = get_weather(city, days)

    # Обрабатываем ошибки, если API вернул ошибку
    if forecast_data.get("error"):
        error_message = forecast_data["error"].get("message", "Неизвестная ошибка")
        await bot.send_message(call.from_user.id, f"Ошибка получения прогноза: {error_message}")
        await bot.answer_callback_query(call.id)
        return

    # Формируем текстовое сообщение на основе полученных данных
    forecast_days = forecast_data.get("forecast", {}).get("forecastday", [])
    text_message = f"<b>Прогноз погоды для {city} на {days} дн. :</b>\n\n"
    for day in forecast_days:
        date = day.get("date")
        day_info = day.get("day", {})
        avg_temp = day_info.get("avgtemp_c")
        condition = day_info.get("condition", {}).get("text")
        emoji = get_condition_emoji(condition)
        text_message += f"{emoji} <b>{date}</b>:\n{condition}, средняя температура {avg_temp}°C\n\n"

    # Отправляем сообщение пользователю
    await bot.send_message(call.from_user.id, text_message, parse_mode=ParseMode.HTML)
    await bot.answer_callback_query(call.id)

    # Добавляем клавиатуру для выбора предыдущего города или нового
    if len(user_city_history.get(call.from_user.id, [])) > 0:
        last_city = user_city_history[call.from_user.id][-1]  # Предыдущий город
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton(f"Последний город: {last_city}", callback_data="previous_city"),
            InlineKeyboardButton("Новый город", callback_data="new_city")
        )
        await bot.send_message(call.from_user.id, "Выбери город:", reply_markup=keyboard)
    else:
        await bot.send_message(call.from_user.id, "Чтобы запросить прогноз для другого города, введи название города.")


#####################
# Обработчик callback-запросов для выбора города
#####################
@dp.callback_query_handler(lambda call: call.data == "previous_city")
async def choose_previous_city(call: CallbackQuery):
    user_id = call.from_user.id
    # Получаем последний город из истории
    last_city = user_city_history.get(user_id, [])[-1]  # Получаем последний город из списка
    if last_city:
        # Устанавливаем выбранный город
        user_city[user_id] = last_city

        # Создаём клавиатуру с выбором периода прогноза
        await send_forecast_keyboard(message=call.message, user_id=user_id)
    else:
        await bot.send_message(user_id, "У вас нет истории городов. Введите новый город.")
        await bot.answer_callback_query(call.id)


@dp.callback_query_handler(lambda call: call.data == "new_city")
async def enter_new_city(call: CallbackQuery):
    await bot.send_message(call.from_user.id, "Введи название нового города.")
    await bot.answer_callback_query(call.id)


# Функция для отправки клавиатуры с выбором периода прогноза
async def send_forecast_keyboard(*,message, user_id) -> None:
    city = user_city.get(user_id)
    if not city:
        return await message.reply("Город не выбран. Введите название города.")

    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton("Сегодня", callback_data="forecast:1"),
        InlineKeyboardButton("3 дня", callback_data="forecast:3"),
        InlineKeyboardButton("Неделя", callback_data="forecast:7")
    )
    await message.reply(f"Город {city} выбран.\nВыбери период прогноза:", reply_markup=keyboard)


def get_condition_emoji(condition_text: str) -> str:
    condition_text = condition_text.lower()
    if "солнечно" in condition_text:
        return "☀️"
    elif "пасмурно" in condition_text:
        return "☁️"
    elif "дождь" in condition_text:
        return "🌧️"
    elif "облачно" in condition_text:
        return "⛅"
    else:
        return "🌈"


# Запускаем бота
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
