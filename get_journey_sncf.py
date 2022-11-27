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

def read_cog(path):
    """
    Read code officiel géographique data, in the level of arrondissement.
    """
    return pd.read_csv(path)

def get_cog(name_city, db_cog):
    """
    Get the corresponding code officiel géographique for a given city, in the level of arrondissement.
    """
    if type(name_city) is float:
        print("Error code")
        return -1
    else:
        code = db_cog.loc[db_cog['NCCENR'] == name_city]['CHEFLIEU'].values
        if len(code) != 1:
            print("Error code")
            return -1
        else:
            return code[0]

'''TO DO check list of parameters'''
def form_parameters(city_depart,
                    city_arrive,
                    date,
                    db_cog,
                    min_nb_journey=3):
    """
    Get the formalised parameters for API
    """
    dt = datetime.strptime(date, '%d/%m/%Y %H:%M:%S')
    t_string = datetime.strftime(dt, '%Y%m%dT%H%M%S')
    params = {'from': "admin:fr:" + get_cog(city_depart, db_cog),
              'to': "admin:fr:" + get_cog(city_arrive, db_cog),
              'datetime': str(t_string),
              'min_nb_journeys': min_nb_journey
        }
    return params

def execute_req(api_url, authorisation, parameters):
    """
    Execute request of data
    """
    r = requests.get(
        api_url,
        params=parameters,
        auth=(authorisation, '')
    )
    if r.status_code != 200:  # see HTTP errors
        print("HTTP ERROR")
        return -1
    else:
        result = json.loads(r.content.decode())
        if 'journeys' in result.keys():
            return result['journeys']
        else:
            print('No data')
            return -1

'''TODO : understand sections(potential error)'''
def read_info_journey(journey):
    """
    Get information of all the journeys
    """
    h_depart = datetime.strptime(journey['departure_date_time'], '%Y%m%dT%H%M%S')
    h_arrive =  datetime.strptime(journey['arrival_date_time'], '%Y%m%dT%H%M%S')
    duration = journey['durations']['total']
    no_train = journey['sections'][-2]['display_informations']['headsign']
    type_train = journey['sections'][-2]['display_informations']['commercial_mode']
    direction = journey['sections'][-2]['display_informations']['direction']
    nb_transfers = journey['nb_transfers']

    return [h_depart, h_arrive, duration, no_train, type_train, direction, nb_transfers]

if __name__ == '__main__':
    auth = "42f6483b-fd9a-483a-89b8-4286395fd523"
    api_url = 'https://api.sncf.com/v1/coverage/sncf/journeys?'
    path = './data/arrondissement_2022.csv'
    db_cog = read_cog(path)

    # get info of SNCF train stations
    # https://ressources.data.sncf.com/api/records/1.0/search/?dataset=liste-des-gares&q=&rows=10000&facet=fret&facet=voyageurs&facet=code_ligne&facet=departemen
    path = './data/referentiel_gares_voyageurs.csv'
    df_station = pd.read_csv(path, sep=';')
    # select only train station not RER etc. Not sure about the meaning of cols...
    df_station = df_station.loc[df_station["Niveau de service"] >= 2]

    o = 'Bordeaux'
    d = list(df_station['Commune'].unique())
    stations_foreign = []
    dt = "28/11/2022 09:00:00"
    results = {}
    for d_city in d:
        if get_cog(d_city, db_cog) == -1:
            print(d_city)
        else:
            params = form_parameters(o, d_city, dt, db_cog, 3)
            r = execute_req(api_url, auth, params)

            if r != -1:
                col_name = ['h_depart', 'h_arrive', 'duration', 'no_train', 'type_train', 'direction', 'nb_transfers']
                info = []
                for journey in r:
                    info.append(read_info_journey(journey))
                df = pd.DataFrame(info, columns=col_name)
                df['waiting_time'] = df['h_depart'].apply(lambda x: (datetime.strptime(dt, '%d/%m/%Y %H:%M:%S') - x).seconds)
                df['total_time'] = df['waiting_time'] + df['duration']
                results[d_city] = df
    print('')






