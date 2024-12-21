#  Подключение библиотек для работы приложения.
from flask import Flask, request, render_template, jsonify
import requests
import json

from dash import Dash, html

#  Создаем объект нашего приложения Flask
app = Flask(__name__)

#  Создаем объект библиотеки Dash и первичная настройка. Настраиваем путь, где будет отображаться наша визуализация.
dash_app = Dash(__name__, server=app, url_base_pathname='/dashboard/')
dash_app.layout = [html.Div(children='Hello World')]

# API-ключ и ссылка для работы API.
API_URL = 'http://dataservice.accuweather.com'
API_KEY = 'cm02hwuwSjzaDH6oXgTX7jO5WIxA5Mal'
# API_KEY = 'ATmBycESdqJd4ApCeQjXmrDKq2EAIvph'

""" WARNING: Все ответы на вопросы по заданиям я представлю в readme файле для удобства. """

# Функция для ключа города.
def get_city_key(city_name):
    search_params = {
        'q': city_name,
        'apikey': API_KEY,
        'language': 'ru-ru'
    }
    response = requests.get(f"{API_URL}/locations/v1/cities/search",
                            params=search_params)

    #  Обработка запроса
    if response.status_code == 200:
        data = response.json()
        if data:
            city_key = data[0]["Key"]
            return city_key
        return None  # В случае, если искомый город не найден.
    else:
        print(f"Ошибка запроса: {response.status_code}")
        return None


#  Функция для получения погодных данных в виде CSV файла
def get_csv_data(cities):
    ...


def get_city_weather_data(city, days):
    city_key = get_city_key(city)

    url = f'{API_URL}/forecasts/v1/daily/{days}day/{city_key}'
    params = {'apikey': API_KEY, 'details': 'true'}

    response = requests.get(url, params=params)

    print(response.json())
    if response.status_code == 200:
        return response.json()
    return None


# Функция для оценки неблагоприятных погодных условий
def check_bad_weather(temp, wind, precipitation):
    '''
    Ниже определю неблагоприятные погодные условия(По моему мнению.)
    :param temp: Ниже -5 или выше 35 градусов по Цельсию.
    :param wind: Скорость ветра более 54 км/ч(15 м/с).
    :param precipitation: Вероятность осадков более 65%
    '''

    if not(-5 < temp < 35) or wind > 54 or precipitation > 65:
        return "Неблагоприятные"
    return "Благоприятные"


#  Основная страница приложения
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        #  Получение городов из формы.
        start_city = request.form['start_city']
        end_city = request.form['end_city']
        extra_cities = request.form.getlist('extra_city')

        # Получение погодных данных для начального города
        start_weather_data = get_city_weather_data(start_city, 1)

        # Получение погодных данных для конечного города
        end_weather_data = get_city_weather_data(end_city, 1)

    return render_template('index2.html')


@app.route('/graphs', methods=['GET'])
def dashboard_page():
    ...


# #  Непосредственно запуск программы.
if __name__ == '__main__':
    app.run(debug=True)
    dash_app.run(debug=True)