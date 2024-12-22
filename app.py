# Подключение библиотек для работы приложения.
import folium
from flask import Flask, request, render_template, jsonify, redirect, url_for
import requests
import json
import csv
import pandas as pd
from dash import Dash, html, dcc
import plotly.graph_objs as go
import dash_leaflet as dl


# Создаем объект нашего приложения Flask
app = Flask(__name__)

# Создаем объект библиотеки Dash и первичная настройка. Настраиваем путь, где будет отображаться наша визуализация.
dash_app = Dash(__name__, server=app, url_base_pathname='/graphs/')
dash_app.layout = html.Div(children='Hello World')  # Временно, будет обновлено позже

# API-ключ и ссылка для работы API.
API_URL = 'http://dataservice.accuweather.com'
API_KEY = 'glUcJC9fMnoKMIZwckRn0IUphmaia1DO'

""" WARNING: Все ответы на вопросы по заданиям я представлю в readme файле для удобства. """
""" Предупреждение! Нельзя найти погоду для 3-х дней с помощью API, поэтому можно будет найти погоду только
на 1 и на 5 дней вперед. """

# Функция для получения ключа города и его координат.
def get_city_key(city_name):
    search_params = {
        'q': city_name,
        'apikey': API_KEY,
        'language': 'ru-ru'
    }
    response = requests.get(f"{API_URL}/locations/v1/cities/search", params=search_params)

    # Обработка запроса
    if response.status_code == 200:
        data = response.json()
        if data:
            city_key = data[0]["Key"]
            latitude = data[0]["GeoPosition"]["Latitude"]
            longitude = data[0]["GeoPosition"]["Longitude"]
            return city_key, latitude, longitude
        return None  # В случае, если искомый город не найден.
    else:
        print(f"Ошибка запроса: {response.status_code}")
        return None

# Функция для получения данных погоды в виде CSV файла. Нужно для работы с графиками.
def save_weather_data_to_csv(weather_data_list, csv_file_path, city_names):
    # Столбцы в нашем CSV файле.
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

                # Запись в CSV файл.
                writer.writerow(weather_data)

def process_weather_data(start_city, end_city, extra_cities, days):
    """ С помощью этой функции мы получаем погодные данные для каждого города.
    После чего вызываем функцию выше и создаем CSV-файл, который уже направится в Plotly и Dash для
    визуализации данных."""

    weather_data_list = []
    cities = [start_city] + extra_cities + [end_city]
    coordinates = []

    # Получение погодных данных для всех городов
    for city in cities:
        city_info = get_city_key(city)
        if city_info:
            city_key, latitude, longitude = city_info
            city_weather = get_city_weather_data(city_key, days)
            if city_weather:
                weather_data_list.append(city_weather)
                coordinates.append((latitude, longitude))
        else:
            print(f"Не удалось получить информацию о городе: {city}")


# Преобразование результатов в CSV-файл.
    save_weather_data_to_csv(weather_data_list, 'weather_data.csv', cities)

    # Сохранение координат в отдельный JSON-файл
    with open('coordinates.json', 'w', encoding='utf-8') as f:
        json.dump({'cities': cities, 'coordinates': coordinates}, f, ensure_ascii=False, indent=4)

    return weather_data_list, cities

def get_city_weather_data(city_key, days):
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
    Ниже определю неблагоприятные погодные условия (по моему мнению).
    :param temp: Ниже -5 или выше 35 градусов по Цельсию.
    :param wind: Скорость ветра более 54 км/ч (15 м/с).
    :param precipitation: Вероятность осадков более 65%
    '''

    if not(-5 < temp < 35) or wind > 54 or precipitation > 65:
        return "Неблагоприятные"
    return "Благоприятные"

# Основная страница приложения
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Получение городов и значение радио-кнопок из формы.
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

def create_route_map(locations, cities):
    # Центрируем карту на первом городе или устанавливаем координаты по умолчанию
    if locations:
        center = locations[0]
    else:
        center = [55.7558, 37.6173]  # Москва по умолчанию

    # Создаем карту с использованием dash_leaflet
    route_map = dl.Map(center=center, zoom=6, children=[
        dl.TileLayer(),  # Базовый слой карты
        # Добавляем маркеры для каждого города
        *[
            dl.Marker(position=loc, children=[
                dl.Popup(html.Div([
                    html.H4(city),
                    # Можно добавить дополнительную информацию, например, текущую погоду
                ]))
            ]) for loc, city in zip(locations, cities)
        ],
        # Рисуем линию маршрута между городами
        dl.Polyline(positions=locations, color='blue', weight=2.5)
    ], style={'width': '100%', 'height': '500px'})

    return route_map

@app.route('/graphs', methods=['GET'])
def graphs():
    # Получаем данные из созданного CSV-файла.
    df = pd.read_csv('weather_data.csv')

    # Получаем координаты из JSON-файла.
    with open('coordinates.json', 'r', encoding='utf-8') as f:
        coord_data = json.load(f)
    cities = coord_data['cities']
    coordinates = coord_data['coordinates']

    # Получение уникальных названий городов
    unique_cities = df['City'].unique()

    # Создание графиков для каждого города
    temp = []
    wind_speed_data = []
    condition_data = []

    for city in unique_cities:
        city_data = df[df['City'] == city]

        # График средней температуры
        temp.append(go.Scatter(
            x=city_data['Date'],
            y=city_data['Average Temperature'],
            mode='lines+markers',
            name=f'Средняя Температура ({city})',
            line=dict(width=2)
        ))

# График скорости ветра
        wind_speed_data.append(go.Scatter(
            x=city_data['Date'],
            y=city_data['Wind Speed'],
            mode='lines+markers',
            name=f'Скорость Ветра ({city})',
            line=dict(width=2)
        ))

        # График условий погоды
        condition_data.append(go.Scatter(
            x=city_data['Date'],
            y=[cities.index(city)] * len(city_data),
            mode='markers',
            name=f'Условия ({city})',
            marker=dict(
                color=city_data['Condition'].map({
                    "Благоприятные": "green",
                    "Неблагоприятные": "red"
                }),
                size=10,
                symbol='circle'
            )
        ))

    # Создание карты маршрута
    route_map = create_route_map(coordinates, cities)

    # Обновление макета Dash-приложения
    dash_app.layout = html.Div(children=[
        html.H1(children='Графики и Маршрут'),

        dcc.Graph(
            id='temperature-graph',
            figure={
                'data': temp,
                'layout': go.Layout(
                    title='Средняя Температура Воздуха',
                    xaxis={'title': 'Дата'},
                    yaxis={'title': 'Температура (°C)'},
                    hovermode='closest'
                )
            }
        ),
        dcc.Graph(
            id='condition-graph',
            figure={
                'data': condition_data,
                'layout': go.Layout(
                    title='Погодные Условия',
                    xaxis={'title': 'Дата'},
                    yaxis={
                        'tickvals': list(range(len(unique_cities))),
                        'ticktext': unique_cities
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
                    title='Скорость Ветра',
                    xaxis={'title': 'Дата'},
                    yaxis={'title': 'Скорость Ветра (миль/час)'},
                    hovermode='closest'
                )
            }
        ),
        html.H2(children='Маршрут'),
        route_map  # Включение карты в макет
    ])

    # Возвращаем HTML-код Dash-приложения
    return dash_app.index()


# Непосредственно запуск программы.
if __name__ == '__main__':
    app.run(debug=True)
    dash_app.run_server(debug=True)  # Удалите или закомментируйте, если используете интеграцию с Flask