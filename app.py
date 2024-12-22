#  Подключение библиотек для работы приложения.
import folium
from flask import Flask, request, render_template, jsonify, redirect, url_for
import requests
import json, csv
import pandas as pd
from dash import Dash, html, dcc
import plotly.graph_objs as go
from geopy.geocoders import Nominatim

#  Создаем объект нашего приложения Flask
app = Flask(__name__)

#  Создаем объект библиотеки Dash и первичная настройка. Настраиваем путь, где будет отображаться наша визуализация.
dash_app = Dash(__name__, server=app, url_base_pathname='/dashboard/')
dash_app.layout = [html.Div(children='Hello World')]

# API-ключ и ссылка для работы API.
API_URL = 'http://dataservice.accuweather.com'
API_KEY = 'glUcJC9fMnoKMIZwckRn0IUphmaia1DO'

""" WARNING: Все ответы на вопросы по заданиям я представлю в readme файле для удобства. """
""" Предупреждение! Нельзя найти погоду для 3-х дней с помощью API, поэтому можно будет найти погоду только
на 1 и на 5 дней вперед. """

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


#  Функция для получения данных погоды в виде СSV файла. Нужно для работы с графиками.
def save_weather_data_to_csv(weather_data_list, csv_file_path, city_names):
    #  Столбцы в нашем CSV файле.
    metrics = ['City', 'Date', 'Average Temperature', 'Wind Speed', 'Precipitation Probability', 'Condition']
    print(len(weather_data_list) == len(city_names))
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=metrics)
        writer.writeheader()
        for i in range(len(weather_data_list)):
            for cityData in weather_data_list[i]['DailyForecasts']:
                date = cityData['Date']
                average_temp = (cityData['Temperature']['Minimum']['Value'] + cityData['Temperature']['Maximum']['Value']) / 2
                wind = cityData['Day']['Wind']['Speed']['Value']
                precipitation_probability = cityData['Day']['PrecipitationProbability']
                weather_condition = check_bad_weather(average_temp, wind, precipitation_probability)

                weather_data = {
                    'City': city_names[i],
                    'Date': date,
                    'Average Temperature': average_temp,
                    'Wind Speed': wind,
                    'Precipitation Probability': precipitation_probability,
                    'Condition': weather_condition
                }

                #  Запись в CSV файл.
                writer.writerow(weather_data)


def process_weather_data(start_city, end_city, extra_cities, days):
    """ С помощью этой функции мы получаем погодные данные для каждого города.
    После чего вызываем функцию выше и создаем CSV-файл, который уже направится в Plotly и Dash для
    визуализации данных."""

    weather_data_list = []
    cities = [start_city] + extra_cities + [end_city]

    # Получение погодных данных для всех городов
    for city in cities:
        city_weather = get_city_weather_data(city, days)
        if city_weather:
            weather_data_list.append(city_weather)

    #  Преобразование результатов в CSV-файл.
    save_weather_data_to_csv(weather_data_list, 'weather_data.csv', cities)

    return weather_data_list, cities


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
        #  Получение городов и значение радио-кнопок из формы.
        start_city = request.form['start_city']
        end_city = request.form['end_city']
        extra_cities = request.form.getlist('extra_city')
        radio_form_result = int(request.form.get('forecast_days'))
        print(radio_form_result)
        weather_data_list, cities = process_weather_data(start_city, end_city, extra_cities, radio_form_result)

        if weather_data_list:
            # Перенаправление на страницу с графиками
            return redirect(url_for('graphs'))

        else:
            return render_template('error.html', message="Ошибка получения данных о погоде.")

    return render_template('index2.html')


def get_location(city_name):
    geolocator = Nominatim(user_agent="weather_app")
    location = geolocator.geocode(city_name)
    if location:
        return [location.latitude, location.longitude]
    else:
        return None


def create_route_map(locations, cities, weather_info):
    # Создаем карту, центрируем на первом городе
    route_map = folium.Map(location=locations[0], zoom_start=6)

    # Добавляем маркеры для каждого города
    for loc, city, weather in zip(locations, cities, weather_info):
        tooltip = f"{city}: {weather}"
        folium.Marker(
            location=loc,
            popup=tooltip,
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(route_map)

    # Рисуем линию маршрута
    folium.PolyLine(locations, color='blue', weight=2.5, opacity=1).add_to(route_map)

    # Сохраняем карту в файл
    route_map.save('static/route_map.html')


@app.route('/graphs', methods=['GET'])
def graphs():
    #  Получаем данные из созданного CSV-файла.
    df = pd.read_csv('weather_data.csv')

    # Получаем уникальные названия городов
    cities = df['City'].unique()

    # Создание графиков для каждого города
    temp = []
    wind_speed_data = []
    condition_data = []

    for city in cities:
        city_data = df[df['City'] == city]

        # График средней температуры
        temp.append(go.Scatter(
            x=city_data['Date'],
            y=city_data['Average Temperature'],
            mode='lines+markers',
            name=f'Average Temperature ({city})',
            line=dict(width=2)
        ))

        # График скорости ветра
        wind_speed_data.append(go.Scatter(
            x=city_data['Date'],
            y=city_data['Wind Speed'],
            mode='lines+markers',
            name=f'Wind Speed ({city})',
            line=dict(width=2)
        ))

        # График условий погоды
        condition_data.append(go.Scatter(
            x=city_data['Date'],
            y=[cities.tolist().index(city)] * len(city_data),  # Используем индекс города для оси Y
            mode='markers',
            name=f'Condition ({city})',
            marker=dict(
                color=city_data['Condition'].map({
                    "благоприятные": "green",
                    "неблагоприятные": "red"
                }),
                size=10,
                symbol='circle'
            )
        ))

    dash_app.layout = html.Div(children=[
        html.H1(children='Графики'),

        dcc.Graph(
            id='temperature-graph',
            figure={
                'data': temp,
                'layout': go.Layout(
                    title='Средняя температура воздуха',
                    xaxis={'title': 'Дата'},
                    yaxis={'title': 'Температура (°F)'},
                    hovermode='closest'
                )
            }
        ),
        dcc.Graph(
            id='condition-graph',
            figure={
                'data': condition_data,
                'layout': go.Layout(
                    title='Погодные условия',
                    xaxis={'title': 'Дата'},
                    yaxis={
                        'tickvals': list(range(len(cities))),  # Индексы городов по оси Y
                        'ticktext': cities  # Названия городов по оси Y
                    },
                    hovermode='closest'
                )
            }
        ),
        dcc.Graph(
            id='wind-speed-graph',
            figure={
                'data': wind_speed_data,
                'layout': go.Layout(
                    title='Скорость ветра',
                    xaxis={'title': 'Дата'},
                    yaxis={'title': 'Скорость вера (миль/час)'},
                    hovermode='closest'
                )
            }
        )
    ])

    # Возвращаем HTML-код Dash-приложения
    return dash_app.index()


# #  Непосредственно запуск программы.
if __name__ == '__main__':
    app.run(debug=True)
    dash_app.run(debug=True)