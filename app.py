#  Подключение библиотек для работы приложения.
from flask import Flask, request, render_template, jsonify
import requests
import json

#  Создаем объект нашего приложения.
app = Flask(__name__)

# API-ключ и ссылка для работы API.
API_URL = 'http://dataservice.accuweather.com'
API_KEY = 'cm02hwuwSjzaDH6oXgTX7jO5WIxA5Mal'


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


# Функция для получения погодных данных
def get_city_weather_data(city):
    #  Получение ключа города. Используется функция выше.
    city_key = get_city_key(city)

    url = f'{API_URL}/currentconditions/v1/{city_key}'
    params = {'apikey': API_KEY, 'details': 'true'}

    #  Генерация запроса.
    response = requests.get(url, params=params)

    #  Обработка полученного ответа.
    if response.status_code == 200:
        return response.json()[0]
    else:
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

        # Получение погодных данных для начального города
        start_weather_data = get_city_weather_data(start_city)

        # Получение погодных данных для конечного города
        end_weather_data = get_city_weather_data(end_city)

        if start_weather_data and end_weather_data:
            # Данные для начального города
            start_temp = start_weather_data['Temperature']['Metric']['Value']
            start_wind = start_weather_data['Wind']['Speed']['Metric']['Value']
            start_precipitation = (start_weather_data['PrecipitationSummary']['Precipitation']['Metric']['Value'] * 100)
            start_city_result = check_bad_weather(start_temp, start_wind, start_precipitation)

            # Данные для конечного города
            end_temp = end_weather_data['Temperature']['Metric']['Value']
            end_speed = end_weather_data['Wind']['Speed']['Metric']['Value']
            end_precipitation = (end_weather_data['PrecipitationSummary']['Precipitation']['Metric']['Value'] * 100)
            end_city_result = check_bad_weather(end_temp, end_speed, end_precipitation)

            return render_template('result2.html',
                                   start_temperature=start_temp,
                                   start_wind_speed=start_wind,
                                   start_precipitation_probability=start_precipitation,
                                   start_weather_condition=start_city_result,
                                   end_temperature=end_temp,
                                   end_wind_speed=end_speed,
                                   end_precipitation_probability=end_precipitation,
                                   end_weather_condition=end_city_result)
        else:
            return render_template('error.html', message="Ошибка получения данных о погоде.")

    return render_template('index2.html')


#  Непосредственно запуск программы.
if __name__ == '__main__':
    app.run(debug=True)
