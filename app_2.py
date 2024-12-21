import asyncio
from flask import Flask, request, render_template, redirect, url_for
import requests
import json
import csv
import dash
from dash import dcc, html
import pandas as pd
import plotly.graph_objs as go


app = Flask(__name__)
dash_app = dash.Dash(__name__, server=app, url_base_pathname='/dashboard/')
dash_app.layout = html.Div()


API_KEY = 'ATmBycESdqJd4ApCeQjXmrDKq2EAIvph'
BASE_URL = 'http://dataservice.accuweather.com'


def save_weather_data_to_csv(weather_data_list, csv_file_path, city_names):
    headers = ['City', 'Date', 'Average Temperature', 'Wind Speed', 'Precipitation Probability', 'Condition']

    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        for i in range(len(weather_data_list)):
            for daily_forecast in weather_data_list[i]['DailyForecasts']:
                date = daily_forecast['Date']
                min_temp = daily_forecast['Temperature']['Minimum']['Value']
                max_temp = daily_forecast['Temperature']['Maximum']['Value']
                average_temperature = (min_temp + max_temp) / 2
                wind_speed = daily_forecast['Day']['Wind']['Speed']['Value']
                precipitation_probability = daily_forecast['Day']['PrecipitationProbability']
                weather_condition = check_bad_weather(average_temperature, wind_speed, precipitation_probability)

                weather_data = {
                    'City': city_names[i],
                    'Date': date,
                    'Average Temperature': average_temperature,
                    'Wind Speed': wind_speed,
                    'Precipitation Probability': precipitation_probability,
                    'Condition': weather_condition
                }
                writer.writerow(weather_data)


def get_city_key(city_name):
    location_url = f"{BASE_URL}/locations/v1/cities/search"
    params = {'q': city_name, 'apikey': API_KEY, 'language': 'ru-ru'}
    response = requests.get(location_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]["Key"]
    return None


def get_weather_data(city, days):
    city_key = get_city_key(city)
    url = f'{BASE_URL}/forecasts/v1/daily/{days}day/{city_key}'
    params = {'apikey': API_KEY, 'details': 'true'}
    response = requests.get(url, params=params)
    print(response.json())
    if response.status_code == 200:
        return response.json()
    return None


def check_bad_weather(temperature, wind_speed, precipitation_value):
    if temperature < 0 or temperature > 35:
        return "неблагоприятные"
    if wind_speed > 50:
        return "неблагоприятные"
    if precipitation_value > 70:
        return "неблагоприятные"
    return "благоприятные"


def process_weather_data(start_city, end_city, intermediate_cities, days):
    # Получение погодных данных для всех городов
    weather_data_list = []
    if len(intermediate_cities) == 0:
        city_names = [start_city] + intermediate_cities + [end_city]
    else:
        city_names = [start_city, end_city]

    # Добавляем начальный город
    start_weather_data = get_weather_data(start_city, days)
    if start_weather_data:
        weather_data_list.append(start_weather_data)

    # Добавляем промежуточные города
    for city in intermediate_cities:
        city_weather_data = get_weather_data(city.strip(), days)  # Убираем лишние пробелы
        if city_weather_data:
            weather_data_list.append(city_weather_data)

    # Добавляем конечный город
    end_weather_data = get_weather_data(end_city, days)
    if end_weather_data:
        weather_data_list.append(end_weather_data)

    save_weather_data_to_csv(weather_data_list, 'weather_forecast.csv', city_names)

    return weather_data_list, city_names


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        start_city = request.form['start_city']
        end_city = request.form['end_city']
        intermediate_cities = request.form.getlist('intermediate_city')
        days = int(request.form['days'])  # Получаем выбранное значение

        weather_data_list, city_names = process_weather_data(start_city, end_city, intermediate_cities, days)

        if weather_data_list:
            # Перенаправление на страницу с графиками
            return redirect(url_for('dashboard'))

        else:
            return render_template('error.html', message="Ошибка получения данных о погоде.")

    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    # Создание графиков на основе данных из CSV файла
    df = pd.read_csv('weather_forecast.csv')

    # Получаем уникальные названия городов
    cities = df['City'].unique()

    # Создание графиков для каждого города
    temperature_data = []
    wind_speed_data = []
    condition_data = []

    for city in cities:
        city_data = df[df['City'] == city]

        # График средней температуры
        temperature_data.append(go.Scatter(
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
        html.H1(children='Weather Forecast'),

        dcc.Graph(
            id='temperature-graph',
            figure={
                'data': temperature_data,
                'layout': go.Layout(
                    title='Average Temperature',
                    xaxis={'title': 'Date'},
                    yaxis={'title': 'Temperature (°F)'},
                    hovermode='closest'
                )
            }
        ),

        dcc.Graph(
            id='wind-speed-graph',
            figure={
                'data': wind_speed_data,
                'layout': go.Layout(
                    title='Wind Speed',
                    xaxis={'title': 'Date'},
                    yaxis={'title': 'Wind Speed (mi/h)'},
                    hovermode='closest'
                )
            }
        ),

        # График условий погоды с несколькими городами
        dcc.Graph(
            id='condition-graph',
            figure={
                'data': condition_data,
                'layout': go.Layout(
                    title='Weather Conditions',
                    xaxis={'title': 'Date'},
                    yaxis={
                        'tickvals': list(range(len(cities))),  # Индексы городов по оси Y
                        'ticktext': cities  # Названия городов по оси Y
                    },
                    hovermode='closest'
                )
            }
        )
    ])

    return dash_app.index()  # Возвращаем HTML-код Dash-приложения


if __name__ == '__main__':
    app.run()
    dash_app.run()
