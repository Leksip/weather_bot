import requests
from config import WEATHER_API_KEY

def get_weather(city, days = 1):
    print(WEATHER_API_KEY)
    url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={city}&days={days}&lang=ru"
    response = requests.get(url)
    return response.json()