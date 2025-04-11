from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ParseMode
from config import BOT_TOKEN
from weatner import get_weather
import json

# Создаём экземпляр бота с токеном
bot = Bot(token=BOT_TOKEN)

# Создаём диспетчер — он распределяет входящие сообщения
dp = Dispatcher(bot)

# Для простоты будем хранить выбранный город каждого пользователя в глобальном словаре.
# В реальном проекте стоит использовать базу данных или state storage.
user_city = {}


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

    # Создаем инлайн-клавиатуру с кнопками для выбора периода прогноза
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton("Сегодня", callback_data="forecast:1"),
        InlineKeyboardButton("3 дня", callback_data="forecast:3"),
        InlineKeyboardButton("Неделя", callback_data="forecast:7")
    )
    await message.reply(f"Город {city} выбран.\nВыбери период прогноза:", reply_markup=keyboard)


#####################
# Обработчик callback-запросов (нажатие на кнопки)
#####################
@dp.callback_query_handler(lambda call: call.data and call.data.startswith("forecast:"))
async def process_forecast_callback(call: CallbackQuery):
    print(f'callback data {call.data}')
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
    print(json.dumps(forecast_data, indent=4, ensure_ascii=False))

    # Обрабатываем ошибки, если API вернул ошибку
    if forecast_data.get("error"):
        error_message = forecast_data["error"].get("message", "Неизвестная ошибка")
        await bot.send_message(call.from_user.id, f"Ошибка получения прогноза: {error_message}")
        await bot.answer_callback_query(call.id)
        return

    # Формируем текстовое сообщение на основе полученных данных
    forecast_days = forecast_data.get("forecast", {}).get("forecastday", [])
    print(forecast_days)
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

    user_city.pop(call.from_user.id, None)

    await bot.send_message(call.from_user.id, "Чтобы запросить прогноз, введи название города.")
    await bot.answer_callback_query(call.id)


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
