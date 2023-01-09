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
import pytz
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


def get_input_coordination(list_coordination):
    '''
    Formaliser les coordinations pour api
    :param list_coordination:
    :return: string
    '''
    strings = ''
    for place in list_coordination:
        strings = strings + str(place[0]) + ',' + str(place[1]) + '|'
    # remove the last |
    return str(strings[:-1])

def execute_req_google(parameters,
                payload={},
                headers={},
                url="https://maps.googleapis.com/maps/api/distancematrix/json?"):
    """
    Execute request of data
    """
    response = requests.request("GET", url, headers=headers, params=parameters, data=payload)
    if response.status_code != 200:  # see HTTP errors
        print(response.status_code)
        return -1
    else:
        result = json.loads(response.content.decode())['rows'][0]['elements'][0]['duration']['value']
        return result


def get_params_google(origin_coord,
               dest_coord,
               departure_time=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
               zone='Europe/Paris',
               mode="driving",
               traffic_mode="best_guess",
               key='AIzaSyDxAF6tBpC7b_gDEf2cQth-weR9schPZ-o'):
    tz = pytz.timezone(zone)
    dt_strp = tz.localize(datetime.strptime(departure_time, '%d/%m/%Y %H:%M:%S'))
    dt_utc = dt_strp.astimezone(pytz.UTC)
    timestamp = int(dt_utc.timestamp())
    param = {"origins": get_input_coordination(origin_coord),
             "destinations": get_input_coordination(dest_coord),
             "departure_time": timestamp,
             "mode": mode,
             "traffic_mode": traffic_mode,
             "language": "fr-FR",
             "key": key}
    return param

if __name__ == '__main__':
    # read data and input parameters
    auth = "42f6483b-fd9a-483a-89b8-4286395fd523"
    api_url = 'https://api.sncf.com/v1/coverage/sncf/journeys?'
    path = './data/arrondissement_2022.csv'
    db_cog = read_cog(path)

    # get info of SNCF train stations
    # https://ressources.data.sncf.com/api/records/1.0/search/?dataset=liste-des-gares&q=&rows=10000&facet=fret&facet=voyageurs&facet=code_ligne&facet=departemen
    path = './data/referentiel_gares_voyageurs.csv'
    df_station = pd.read_csv(path, sep=';')
    # select only train station not only for region
    df_station = df_station.loc[df_station["Niveau de service"] >= 2]
    df_station_foreign = pd.read_csv('./data/gares_etrangeres.csv', usecols=['name', 'id', 'lat', 'lon', 'city'])
    df_city_coord = pd.read_csv('./data/coord_city.csv')

    # search OD and time
    '''==============================================TO SET=========================================================='''
    o_ville = 'Paris'
    dt0 = "10/01/2023 17:00:00"
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
            params = {'from': "admin:fr:" + get_cog(o_ville, db_cog),
                      'to': station_d[1]['id'],
                      'datetime': str(t_string),
                      'min_nb_journeys': 3,
                      'max_nb_transfers': 2
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
                df['depart'] = o_ville
                df['arrival'] = station_d[1]['name']
                df_city.append(df)
        print(city_d + ' done !')
        if df_city:
            results[city_d] = pd.concat(df_city)

    # get info for destinations in France
    for d_city in d:
        if get_cog(d_city, db_cog) == -1:
            print(d_city + 'not found')
        else:
            params = form_parameters(o_ville, d_city, dt0, db_cog, 1)
            r = execute_req(api_url, auth, params)

            if r != -1:
                info = []
                for journey in r:
                    info.append(read_info_journey(journey))
                df = pd.DataFrame(info, columns=col_name)
                df['waiting_time'] = df['h_depart'].apply(lambda x: (x - dt).seconds)
                df['total_time'] = df['waiting_time'] + df['duration']
                df['depart'] = o_ville
                df['arrival'] = d_city
                results[d_city] = df

    # save results
    results_df = pd.concat(results.values(), ignore_index=True)
    depart_gares = results_df[['station_orig', 'station_orig_lat', 'station_orig_lon', 'depart']].copy()
    depart_gares.drop_duplicates(inplace=True, ignore_index=True)
    arrival_gares = results_df[['station_dest', 'station_dest_lat', 'station_dest_lon', 'arrival']].copy()
    arrival_gares.drop_duplicates(inplace=True, ignore_index=True)
    depart_gares = depart_gares.merge(df_city_coord, left_on='depart', right_on='city')
    arrival_gares = arrival_gares.merge(df_city_coord, left_on='arrival', right_on='city')
    depart_gares['duration_1'] = 0
    for i in range(len(depart_gares)):
        o = [[depart_gares['lat_city'][i], depart_gares['lon_city'][i]]]
        d = [[depart_gares['station_orig_lat'][i], depart_gares['station_orig_lon'][i]]]
        parameters = get_params_google(o, d, dt0)
        depart_gares['duration_1'][i] = execute_req_google(parameters)
    arrival_gares['duration_2'] = 0
    for i in range(len(arrival_gares)):
        d = [[arrival_gares['lat_city'][i], arrival_gares['lon_city'][i]]]
        o = [[arrival_gares['station_dest_lat'][i], arrival_gares['station_dest_lon'][i]]]
        parameters = get_params_google(o, d, dt0)
        arrival_gares['duration_2'][i] = execute_req_google(parameters)
    results_df = results_df.merge(depart_gares, left_on='station_orig', right_on='station_orig')
    results_df = results_df.merge(arrival_gares, left_on='station_dest', right_on='station_dest')
    print(results_df.columns)
    results_df = results_df[['h_depart', 'h_arrive', 'station_orig', 'station_orig_lat_x', 'station_orig_lon_x',
                             'duration', 'nb_transfers', 'station_dest', 'station_dest_lat_x', 'station_dest_lon_x',
                             'waiting_time', 'total_time', 'depart_x', 'arrival_x', 'duration_1', 'lat_city_y',
                             'lon_city_y', 'duration_2']]
    results_df['waiting_time'] = results_df['waiting_time'] - results_df['duration_1']
    results_df['total_time'] = results_df['total_time'] + results_df['duration_2']
    results_df.loc[results_df['waiting_time'] > 0].to_csv('trajets' + '_' + o_ville + '_' + t_string + '.csv')
    total_time = {}
    city_d = list(results.keys())[0]
    cols = list(results[city_d].columns)
    for city in results.keys():
        total_time[city] = results[city].loc[results[city]['total_time'] == min(results[city]['total_time'])].values.tolist()[0] # if several journeys with same duration, keep the first
    # the trip with min duration(in train and transfer) for each destination city not station
    total_time = pd.DataFrame.from_dict(total_time, orient='index', columns=cols)
    with open('results_' + o_ville + '.pickle', 'wb') as f:
        pickle.dump(results, f)
    total_time.to_csv('results' + '_' + o_ville + '_' + t_string + '.csv')

