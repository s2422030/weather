import json
import flet as ft
import requests
import os


def main(page: ft.Page):
    # JSONファイルの絶対パスまたは相対パスを指定
    json_file_path = os.path.join(os.path.dirname(__file__), 'areas.json')

    # JSONデータを読み込む
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except FileNotFoundError as e:
        print(f"JSONファイルが見つかりません: {e.filename}")
        return
    except IOError as e:
        print(f"JSONファイルの読み込みに失敗しました: {e.strerror}")
        return

    # JSONデータの構造を表示してデバッグ
    print(json.dumps(json_data, indent=4, ensure_ascii=False))

    offices = json_data.get("offices", {})
    centers = json_data.get("centers", {})

    # 地方リストの作成
    def get_region_options():
        return [ft.dropdown.Option(key, value.get("name", "Unknown")) for key, value in centers.items()]

    def on_region_select(e):
        selected_region_code = e.control.value
        prefectures = centers.get(selected_region_code, {}).get("children", [])

        if not prefectures:
            print(f"Error: No prefectures found for region code {selected_region_code}")
            return

        # デバッグ: 選択された地方の都道府県リストを表示
        print(f"Selected region code: {selected_region_code}")
        print(f"Prefectures: {prefectures}")

        # 都道府県リストの作成
        prefecture_options = [ft.dropdown.Option(code, offices.get(code, {}).get("name", "Unnamed Area")) for code in prefectures]

        # デバッグ: 都道府県リストの表示
        for option in prefecture_options:
            print(f"Prefecture option: {option.key} - {option.text}")

        prefecture_dropdown.options = prefecture_options
        prefecture_dropdown.visible = True
        small_area_dropdown.options = []
        small_area_dropdown.visible = False
        page.update()

    def on_prefecture_select(e):
        selected_prefecture_code = e.control.value
        small_areas = offices.get(selected_prefecture_code, {}).get("children", [])

        if not small_areas:
            print(f"Error: No small areas found for prefecture code {selected_prefecture_code}")
            return

        # 市区町村の名前をAPIから取得する
        pref_code = selected_prefecture_code
        weather_response = requests.get(f"https://www.jma.go.jp/bosai/forecast/data/forecast/{pref_code}.json")
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        area_name_map = {area["area"]["code"]: area["area"]["name"] for area in weather_data[0]["timeSeries"][0]["areas"]}

        # 市区町村リストの作成
        small_area_options = [ft.dropdown.Option(code, area_name_map.get(code, "Unnamed Area")) for code in small_areas]

        # デバッグ: 市区町村リストの表示
        for option in small_area_options:
            print(f"Small Area option: {option.key} - {option.text}")

        small_area_dropdown.options = small_area_options
        small_area_dropdown.visible = True
        page.update()

    def on_small_area_select(e):
        selected_area_code = e.control.value
        selected_area_name = next((option.text for option in small_area_dropdown.options if option.key == selected_area_code), "Unknown")
        print(f"Selected Area: {selected_area_name} ({selected_area_code})")  # デバッグ用メッセージ
        get_weather(selected_area_code, selected_area_name)

    def get_weather(area_code, area_name):
        try:
            pref_code = area_code[:2] + "0000"
            weather_response = requests.get(f"https://www.jma.go.jp/bosai/forecast/data/forecast/{pref_code}.json")
            weather_response.raise_for_status()
            weather_data = weather_response.json()

            try:
                forecasts = f"地域: {area_name}（{area_code}）\n"
                time_series = weather_data[0]["timeSeries"]

                # デバッグで timeSeries の内容を表示
                print(f"timeSeries: {json.dumps(time_series, indent=2)}")

                for area in time_series[0]["areas"]:
                    if area["area"]["code"] == area_code:
                        for i in range(3):  # 3日分の天気予報を取得
                            date = time_series[0]["timeDefines"][i]
                            weather = area["weathers"][i]
                            weather_code = area["weatherCodes"][i]
                            wind = area["winds"][i]
                            wave = area.get("waves", ["情報なし"] * 3)[i]

                            forecast = f"日付: {date}\n天気: {weather}\n風: {wind}\n波: {wave}\n"

                        

                            print(forecast)
                            forecasts += forecast + "\n---------------------------\n"

                result_container.value = forecasts
                page.update()
            except (IndexError, KeyError) as e:
                print(f"天気データの解析に失敗しました: {e}")
        except requests.RequestException as e:
            print(f"天気情報の取得に失敗しました: {e}")

    region_dropdown = ft.Dropdown(
        label="地方を選択",
        options=get_region_options(),
        on_change=on_region_select,
        width=300  # ドロップダウンの幅を指定
    )

    prefecture_dropdown = ft.Dropdown(
        label="都道府県を選択",
        options=[],
        visible=False,
        on_change=on_prefecture_select,
        width=300  # ドロップダウンの幅を指定
    )

    small_area_dropdown = ft.Dropdown(
        label="市区町村を選択",
        options=[],
        visible=False,
        on_change=on_small_area_select,
        width=300  # ドロップダウンの幅を指定
    )

    result_container = ft.Markdown(value="", expand=True)  # expand=Trueで右側にスペースを確保

    page.add(
        ft.Row([
            ft.Column([region_dropdown, prefecture_dropdown, small_area_dropdown], expand=False),  # expand=Falseで左側の固定幅
            result_container
        ])
    )

ft.app(target=main)