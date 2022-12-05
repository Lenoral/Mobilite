# Useful packages
import os
import numpy as np
import pandas as pd
import io
import json
import datetime as pkgdt
import time
import requests 
from requests.adapters import HTTPAdapter
import itertools # list operators
from tqdm import tqdm


def page_gares(numero_page) :
    return requests.get(
        ('https://api.sncf.com/v1/coverage/sncf/stop_areas?start_page={}').format(numero_page),
        auth=('16cbfb01-1943-471f-aac9-7a1139abab77', ''))

######################################
# on commence par la première page qui nous donne le nombre de résultats par page ainsi que le nombre total de résultats

page_initiale = page_gares(0)
item_per_page = page_initiale.json()['pagination']['items_per_page']
total_items = page_initiale.json()['pagination']['total_result']
dfs = []

# on fait une boucle sur toutes les pages suivantes
print_done = {}

for page in range(int(total_items/item_per_page)+1) :
    stations_page = page_gares(page)

    ensemble_stations = stations_page.json()

    if 'stop_areas' not in ensemble_stations:
        # pas d'arrêt
        continue

    # on ne retient que les informations qui nous intéressent
    for station in ensemble_stations['stop_areas']:

        station['lat'] = station['coord']['lat']
        station["lon"]  = station['coord']['lon']

    stations = ensemble_stations['stop_areas']
    dp = pd.DataFrame(stations)

    dfs.append(dp)
    if page % 10 == 0:
        print("Page", page, "---", dp.shape)
        
gares = pd.concat(dfs)
gares.to_csv("./Data/ensemble_gares.csv")
print(gares.shape)
gares.head()

