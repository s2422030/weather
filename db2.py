import sqlite3
import json
import flet as ft
import requests
import os

# データベースのセットアップ
def setup_database():
    conn = sqlite3.connect('forecast_data.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS regions (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS prefectures (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            region_code TEXT,
            FOREIGN KEY (region_code) REFERENCES regions (code)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS areas (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            prefecture_code TEXT,
            FOREIGN KEY (prefecture_code) REFERENCES prefectures (code)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_code TEXT,
            date TEXT,
            weather TEXT,
            wind TEXT,
            wave TEXT,
            FOREIGN KEY (area_code) REFERENCES areas (code)
        )
    ''')

    conn.commit()
    conn.close()

# 天気予報データを挿入する
def insert_weather_data(area_code, area_name, forecasts):
    try:
        conn = sqlite3.connect('forecast_data.db')
        c = conn.cursor()

        print(f"Inserting area: {area_code}, {area_name}")
        c.execute('''
            INSERT OR IGNORE INTO areas (code, name) VALUES (?, ?)
        ''', (area_code, area_name))

        for forecast in forecasts:
            print(f"Inserting weather data: {forecast}")
            c.execute('''
                INSERT INTO weather (area_code, date, weather, wind, wave) VALUES (?, ?, ?, ?, ?)
            ''', (area_code, forecast['date'], forecast['weather'], forecast['wind'], forecast['wave']))

        conn.commit()
        print("Data committed to the database.")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        
    finally:
        conn.close()
        print("Database connection closed.")
        
def insert_data_from_json(json_file_path):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except FileNotFoundError as e:
        print(f"JSONファイルが見つかりません: {e.filename}")
        return
    except IOError as e:
        print(f"JSONファイルの読み込みに失敗しました: {e.strerror}")
        return

    offices = json_data.get("offices", {})
    centers = json_data.get("centers", {})

    print("Inserting data into the database...")
    try:
        conn = sqlite3.connect('forecast_data.db')
        c = conn.cursor()

        for region_code, region_data in centers.items():
            region_name = region_data.get("name")
            print(f"Inserting region: {region_code}, {region_name}")
            c.execute('''
                INSERT OR IGNORE INTO regions (code, name) VALUES (?, ?)
            ''', (region_code, region_name))

            for prefecture_code in region_data.get("children", []):
                prefecture_name = offices.get(prefecture_code, {}).get("name")
                print(f"Inserting prefecture: {prefecture_code}, {prefecture_name}, {region_code}")
                c.execute('''
                    INSERT OR IGNORE INTO prefectures (code, name, region_code) VALUES (?, ?, ?)
                ''', (prefecture_code, prefecture_name, region_code))

        conn.commit()
        print("Data inserted successfully.")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()
            print("SQLite connection closed.")

# データベースのセットアップ実行
setup_database()

# JSONファイルのパスを指定
json_file_path = os.path.join(os.path.dirname(__file__), 'areas.json')

# JSONファイルからデータを挿入
insert_data_from_json(json_file_path)

# 過去のデータや天気予報を表示するための関数
def main(page: ft.Page):
    json_file_path = os.path.join(os.path.dirname(__file__), 'areas.json')

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except FileNotFoundError as e:
        print(f"JSONファイルが見つかりません: {e.filename}")
        return
    except IOError as e:
        print(f"JSONファイルの読み込みに失敗しました: {e.strerror}")
        return

    offices = json_data.get("offices", {})
    centers = json_data.get("centers", {})

    def get_region_options():
        return [ft.dropdown.Option(key, value.get("name", "Unknown")) for key, value in centers.items()]

    def on_region_select(e):
        selected_region_code = e.control.value
        prefectures = centers.get(selected_region_code, {}).get("children", [])

        if not prefectures:
            print(f"Error: No prefectures found for region code {selected_region_code}")
            return

        prefecture_options = [ft.dropdown.Option(code, offices.get(code, {}).get("name", "Unnamed Area")) for code in prefectures]

        prefecture_dropdown.options = prefecture_options
        prefecture_dropdown.visible = True
        small_area_dropdown.options = []
        small_area_dropdown.visible = False
        date_dropdown.options = []
        date_dropdown.visible = False
        page.update()

    def on_prefecture_select(e):
        selected_prefecture_code = e.control.value
        small_areas = offices.get(selected_prefecture_code, {}).get("children", [])

        if not small_areas:
            return

        pref_code = selected_prefecture_code

        try:
            weather_response = requests.get(f"https://www.jma.go.jp/bosai/forecast/data/forecast/{pref_code}.json")
            weather_response.raise_for_status()
            weather_data = weather_response.json()
        except requests.RequestException as re:
            print(f"天気情報の取得に失敗しました: {re}")
            return

        area_name_map = {area["area"]["code"]: area["area"]["name"] for area in weather_data[0]["timeSeries"][0]["areas"]}
        small_area_options = [ft.dropdown.Option(code, area_name_map.get(code, "Unnamed Area")) for code in small_areas]

        small_area_dropdown.options = small_area_options
        small_area_dropdown.visible = True
        date_dropdown.options = []
        date_dropdown.visible = False
        page.update()

    def on_small_area_select(e):
        selected_area_code = e.control.value
        selected_area_name = next((option.text for option in small_area_dropdown.options if option.key == selected_area_code), "Unknown")
        get_weather_dates(selected_area_code)

    def get_weather_dates(area_code):
        conn = sqlite3.connect('forecast_data.db')
        c = conn.cursor()

        c.execute('''
            SELECT DISTINCT date FROM weather WHERE area_code = ?
        ''', (area_code,))

        dates = [row[0] for row in c.fetchall()]
        conn.close()

        date_options = [ft.dropdown.Option(date, date) for date in dates]
        date_dropdown.options = date_options
        date_dropdown.visible = True
        page.update()

    def on_date_select(e):
        selected_date = e.control.value
        selected_area_code = small_area_dropdown.value
        display_weather(selected_area_code, selected_date)

    def display_weather(area_code, selected_date):
        conn = sqlite3.connect('forecast_data.db')
        c = conn.cursor()

        c.execute('''
            SELECT date, weather, wind, wave FROM weather WHERE area_code = ? AND date = ?
        ''', (area_code, selected_date))

        result = c.fetchall()
        conn.close()

        result_markdown = ""
        for row in result:
            result_markdown += f"日付: {row[0]}\n天気: {row[1]}\n風: {row[2]}\n波: {row[3]}\n\n"

        if not result_markdown:
            result_markdown = "選択された日付にデータが見つかりませんでした。"
        
        result_container.value = result_markdown
        page.update()

    region_dropdown = ft.Dropdown(
        label="地方を選択",
        options=get_region_options(),
        on_change=on_region_select,
        width=300
    )

    prefecture_dropdown = ft.Dropdown(
        label="都道府県を選択",
        options=[],
        visible=False,
        on_change=on_prefecture_select,
        width=300
    )

    small_area_dropdown = ft.Dropdown(
        label="市区町村を選択",
        options=[],
        visible=False,
        on_change=on_small_area_select,
        width=300
    )

    date_dropdown = ft.Dropdown(
        label="日付を選択",
        options=[],
        visible=False,
        on_change=on_date_select,
        width=300
    )

    result_container = ft.Markdown(value="", expand=True)

    page.add(
        ft.Row([
            ft.Column([
                region_dropdown,
                prefecture_dropdown,
                small_area_dropdown,
                date_dropdown,
            ], expand=False),
            result_container
        ])
    )

# Fletアプリの実行
ft.app(target=main)

# データベースの内容確認用関数
def check_database():
    conn = sqlite3.connect('forecast_data.db')
    c = conn.cursor()

    print("Checking regions table:")
    for row in c.execute('SELECT * FROM regions'):
        print(row)

    print("Checking prefectures table:")
    for row in c.execute('SELECT * FROM prefectures'):
        print(row)

    print("Checking areas table:")
    for row in c.execute('SELECT * FROM areas'):
        print(row)

    print("Checking weather table:")
    for row in c.execute('SELECT * FROM weather'):
        print(row)

    conn.close()

check_database()