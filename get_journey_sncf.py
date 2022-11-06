# Useful packages
import os
import numpy as np
import pandas as pd
import io
import json
from datetime import datetime
import time
import requests
from requests.adapters import HTTPAdapter
import itertools  # list operators

'''TODO : understand sections(potential error), corresponding code geograph'''
def read_info_journey(journey):
    h_depart = datetime.strptime(journey['departure_date_time'], '%Y%m%dT%H%M%S')
    h_arrive =  datetime.strptime(journey['arrival_date_time'], '%Y%m%dT%H%M%S')
    duration = journey['durations']['total']
    no_train = journey['sections'][-2]['display_informations']['headsign']
    type_train = journey['sections'][-2]['display_informations']['commercial_mode']
    direction = journey['sections'][-2]['display_informations']['direction']
    nb_transfers = journey['nb_transfers']
    return [h_depart, h_arrive, duration, no_train, type_train, direction, nb_transfers]

if __name__ == '__main__':
    api_url = 'https://api.sncf.com/v1/coverage/sncf/journeys?'
    auth =  "42f6483b-fd9a-483a-89b8-4286395fd523"
    O = 'Paris'
    D = 'Lyon'
    dt = datetime.strptime("12/11/2022", '%d/%m/%Y')
    t_start = datetime.strftime(dt, '%Y%m%dT%H%M%S')

    # Parameters
    params_val = {'from': "admin:fr:75056",
                  'to': "admin:fr:69123",
                  'datetime': str(t_start),
                  'min_nb_journeys': 3
        }

    #API query
    r = requests.get(
        api_url,
        params = params_val,
        auth=(auth, '')
    )
    if r.status_code != 200:  # see HTTP errors
        print("HTTP ERROR")
    else:
        results = json.loads(r.content.decode())['journeys']
        col_name = ['h_depart', 'h_arrive', 'duration', 'no_train', 'type_train', 'direction', 'nb_transfers']
        info = []
        for journey in results:
            info.append(read_info_journey(journey))
        df = pd.DataFrame(info, columns=col_name)
        print(df.columns)




