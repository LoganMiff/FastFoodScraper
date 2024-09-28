import requests
from bs4 import BeautifulSoup

import sqlite3 as sql

import string

ff_nutrition_cite: str = "https://fastfoodnutrition.org"

ff_home: str = ff_nutrition_cite + "/fast-food-restaurants"

db_connection = sql.connect("fast_food.db")

db_cursor = db_connection.cursor()

#Accesses a cite, returning its html as a BeautifulSoup object
def getCiteSoup(cite: str) -> BeautifulSoup:
    header: dict = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0"}
    request = requests.get(cite, headers=header)

    page_content: bytes = request.content

    request.close()

    return BeautifulSoup(page_content, "html.parser")

acceptable_macros = ("Calories", "Cholesterol", "Total Fat", "Sodium", "Total Carbohydrates", "Protein")

#Gathers the nutritional data from a given page into a tuple
def getNutritionData(ff_item_nutr_page: BeautifulSoup) -> tuple:
    ff_item_nutr_table: BeautifulSoup = ff_item_nutr_page.find("table", class_="item_nutrition")

    if not ff_item_nutr_table:
        return ()

    ff_item_macros: list[BeautifulSoup] = ff_item_nutr_table.find_all("td", title=True, class_=False, colspan=False)

    nutr_data: tuple = ()

    for ff_item_macro in ff_item_macros:
        ff_item_macro_bold_name = ff_item_macro.previous_sibling.previous_sibling.a

        if not ff_item_macro_bold_name:
            continue

        ff_item_macro_name = ff_item_macro_bold_name.text.strip()

        if ff_item_macro_name not in acceptable_macros:
            continue
        
        unit_strip: int
        
        match ff_item_macro_name:
            case "Cholesterol" | "Sodium":
                unit_strip = -2
            case "Total Fat" | "Total Carbohydrates" | "Protein":
                unit_strip = -1
            case _:
                unit_strip = 6

        ff_item_pure_macro: str = ff_item_macro.text.strip()[:unit_strip]

        if "?" in ff_item_pure_macro:
            ff_item_pure_macro = "0"
            unit_strip = 1

        if "=" in ff_item_pure_macro:
            ff_item_pure_macro = ff_item_pure_macro.split("=")[0]

        nutr_data += (float(ff_item_pure_macro),)

    if len(nutr_data) < len(acceptable_macros):
        if len(nutr_data) == 1:
            return ()
        
        nutr_data = nutr_data[:1] + (0,) + nutr_data[1:]

    print(nutr_data)

    return nutr_data

ff_parent_cite: BeautifulSoup = getCiteSoup(ff_home)

#Gets all fast food places' pages
ff_places_table: BeautifulSoup = ff_parent_cite.find_all("div", class_="filter_target col-6 col-sm-6 col-md-4")

ff_place_list: list[str] = []
ff_place_names: list[str] = ["seven_eleven"]

for ff_place in ff_places_table:
    ff_place_list.append(ff_nutrition_cite + ff_place.a['href'])
    ff_place_names.append(ff_place.a['href'][1:].replace("-", "_"))

ff_place_names.pop(1)

#Gets all fast food places' item nutrition pages
for ff_place_index in range(0, len(ff_place_names)):

    ff_place_name = ff_place_names[ff_place_index]

    print("\nFast Food Place: ", ff_place_name, "\n")

    db_cursor.execute("CREATE TABLE IF NOT EXISTS " + ff_place_name + "(id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, calories INTEGER, fat FLOAT, cholesterol FLOAT, sodium FLOAT, charbs FLOAT, protein FLOAT)")

    ff_food_categories: BeautifulSoup = getCiteSoup(ff_place_list[ff_place_index]).find_all("ul", class_="list rest_item_list ab1")

    ff_item_nutr_list: list = []
    ff_item_names: list = []

    for ff_food_items in ff_food_categories:
        for ff_food_item in ff_food_items.children:
            ff_item_nutr_list.append(ff_nutrition_cite + ff_food_item.a['href'])
            ff_item_names.append(string.capwords(ff_food_item.a['href'].split("/")[2].replace("-", " ")))

    ff_item_index = 0
    ff_item_list_size = len(ff_item_nutr_list)

    #Gathers the nutritional data from the sites, storing them in db
    ff_item_nutr_data: list[tuple] = []

    while ff_item_index < ff_item_list_size:
        ff_item_nutr = ff_item_nutr_list[ff_item_index]
        ff_item_name = ff_item_names[ff_item_index]

        print(ff_item_name, ": ", ff_item_nutr)

        ff_item_index += 1

        ff_item_nutr_page: BeautifulSoup = getCiteSoup(ff_item_nutr)

        ff_item_option_div: BeautifulSoup = ff_item_nutr_page.find("div", class_="dropdown")

        if ff_item_option_div:
            ff_item_options: BeautifulSoup = ff_item_option_div.div

            for ff_option in ff_item_options.contents[1:-1]:
                ff_item_nutr_list.append(ff_nutrition_cite + ff_option['href'])
                ff_item_names.append(string.capwords(ff_option['href'].split("/")[2].replace("-", " ") + " " + ff_option['href'].split("/")[3].replace("-", " ")))
                print("    ", ff_nutrition_cite + ff_option['href'])

            ff_item_index -= 1
            ff_item_list_size -= 1

            ff_item_nutr_list.pop(ff_item_index)
            ff_item_names.pop(ff_item_index)

            continue
        
        item_data = (ff_item_name,) + getNutritionData(ff_item_nutr_page)

        if len(item_data) < 7:
            print("\n404, page defunct\n")

            ff_item_index -= 1
            ff_item_list_size -= 1

            ff_item_nutr_list.pop(ff_item_index)
            ff_item_names.pop(ff_item_index)

            continue

        ff_item_nutr_data.append(item_data)

    print("\nOptions\n")

    for ff_options_nutr in ff_item_nutr_list[ff_item_list_size:]:
        print(ff_item_names[ff_item_index], ": ", ff_options_nutr)

        ff_item_nutr_page: BeautifulSoup = getCiteSoup(ff_options_nutr)
        
        item_data = (ff_item_names[ff_item_index],) + getNutritionData(ff_item_nutr_page)

        if len(item_data) < 7:
            print("\n404, page defunct\n")

            ff_item_index -= 1
            ff_item_list_size -= 1

            ff_item_nutr_list.pop(ff_item_index)
            ff_item_names.pop(ff_item_index)

            continue

        ff_item_nutr_data.append(item_data)

        ff_item_index += 1

    print("\nInserting...")

    db_cursor.executemany("INSERT INTO " + ff_place_name + " VALUES(?, ?, ?, ?, ?, ?, ?)", ff_item_nutr_data)
    db_connection.commit()

    print("Inserted!\n")