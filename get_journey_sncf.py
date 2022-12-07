# Useful packages
import os
import numpy as np
import pandas as pd
import io
import json
import csv
from datetime import datetime
import time
import requests
import pickle
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
            print("City not found:" + name_city)
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
    station_orig = journey['sections'][1]['from']['stop_point']['name']
    station_orig_lat = journey['sections'][1]['from']['stop_point']['coord']['lat']
    station_orig_lon = journey['sections'][1]['from']['stop_point']['coord']['lon']
    station_dest = journey['sections'][-2]['to']['stop_point']['name']
    station_dest_lat = journey['sections'][-2]['to']['stop_point']['coord']['lat']
    station_dest_lon = journey['sections'][-2]['to']['stop_point']['coord']['lon']
    # no_train = journey['sections'][-2]['display_informations']['headsign']
    # type_train = journey['sections'][-2]['display_informations']['commercial_mode']
    # direction = journey['sections'][-2]['display_informations']['direction']
    nb_transfers = journey['nb_transfers']

    return [h_depart, h_arrive, station_orig, station_orig_lat, station_orig_lon, duration, nb_transfers,
        station_dest, station_dest_lat, station_dest_lon]
    # return [h_depart, h_arrive, duration, no_train, type_train, direction, nb_transfers]


if __name__ == '__main__':
    # read data and input parameters
    auth = "16cbfb01-1943-471f-aac9-7a1139abab77"
    api_url = 'https://api.sncf.com/v1/coverage/sncf/journeys?'
    path = './Data/arrondissement_2022.csv'
    db_cog = read_cog(path)

    # get info of SNCF train stations
    # https://ressources.data.sncf.com/api/records/1.0/search/?dataset=liste-des-gares&q=&rows=10000&facet=fret&facet=voyageurs&facet=code_ligne&facet=departemen
    path = './Data/referentiel_gares_voyageurs.csv'
    df_station = pd.read_csv(path, sep=';')
    # select only train station not only for region
    df_station = df_station.loc[df_station["Niveau de service"] >= 0]
    df_station_foreign = pd.read_csv('./Data/gares_etrangeres.csv', usecols=['name', 'id', 'lat', 'lon', 'city'])

    # search OD and time
    '''==============================================TO SET=========================================================='''
    o = 'Bordeaux'
    dt0 = "06/12/2022 10:45:00"
    '''=============================================================================================================='''
    dt = datetime.strptime(dt0, '%d/%m/%Y %H:%M:%S')
    t_string = datetime.strftime(dt, '%Y%m%dT%H%M%S')
    # all possible destination in France
    d = list(df_station['Commune'].unique())
    # possible foreign destination for SNCF,
    d_e = df_station_foreign['city'].unique()
    # d_e = ['Genève']
    # d = ['Lyon']

    # define information for each trip
    # col_name = ['h_depart', 'h_arrive', 'duration', 'no_train', 'type_train', 'direction', 'nb_transfers']
    col_name = ['h_depart', 'h_arrive', 'station_orig', 'station_orig_lat', 'station_orig_lon', 'duration', 'nb_transfers',
                'station_dest', 'station_dest_lat', 'station_dest_lon']
    results = {}

    # get info for foreign destinations
    for city_d in d_e:
        df_city = []
        for station_d in df_station_foreign.loc[df_station_foreign['city'] == city_d].iterrows():
            params = {'from': "admin:fr:" + get_cog(o, db_cog),
                      'to': station_d[1]['id'],
                      'datetime': str(t_string),
                      'min_nb_journeys': 3,
                      'max_nb_transfers': 0
                  }
            r = execute_req(api_url, auth, params)
            if r != -1:
                info = []
                for journey in r:
                    info.append(read_info_journey(journey))
                df = pd.DataFrame(info, columns=col_name)
                df['waiting_time'] = df['h_depart'].apply(
                    lambda x: (x - dt).seconds)
                df['total_time'] = df['waiting_time'] + df['duration']
                df['depart'] = o
                df['arrival'] = station_d[1]['name']
                df_city.append(df)
        print(city_d + ' done !')
        if df_city:
            results[city_d] = pd.concat(df_city)

    # get info for destinations in France
    for d_city in d:
        if get_cog(d_city, db_cog) == -1:
            print(str(d_city) + 'not found')
        else:
            params = form_parameters(o, d_city, dt0, db_cog, 1)
            r = execute_req(api_url, auth, params)

            if r != -1:
                info = []
                for journey in r:
                    info.append(read_info_journey(journey))
                df = pd.DataFrame(info, columns=col_name)
                df['waiting_time'] = df['h_depart'].apply(lambda x: (x - dt).seconds)
                df['total_time'] = df['waiting_time'] + df['duration']
                df['depart'] = o
                df['arrival'] = d_city
                results[d_city] = df

    total_time = {}
    cols = list(results[city_d].columns)
    for city in results.keys():
        total_time[city] = results[city].loc[results[city]['duration'] == min(results[city]['duration'])].values.tolist()[0] # if several journeys with same duration, keep the first
    # the trip with min duration(in train and transfer) for each destination city not station
    total_time = pd.DataFrame.from_dict(total_time, orient='index', columns=cols)

    # save results
    results_df = pd.concat(results.values(), ignore_index=True)
    results_df.to_csv('trajets' + '_' + o + '_' + t_string + '.csv')
    with open('results_' + o + '.pickle', 'wb') as f:
        pickle.dump(results, f)
    total_time.to_csv('results' + '_' + o + '_' + t_string + '.csv')
