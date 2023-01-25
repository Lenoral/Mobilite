import requests
import pandas as pd
import pytz
import json
from datetime import datetime


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


def execute_req(parameters,
                payload={},
                headers={},
                url="https://maps.googleapis.com/maps/api/distancematrix/json?"):
    """
    Execute request of data
    """
    response = requests.request("GET", url, headers=headers, params=parameters, data=payload)
    if response.status_code != 200:  # see HTTP errors
        print("HTTP ERROR")
        return -1
    else:
        l = []
        result = json.loads(response.content.decode())['rows'][0]['elements']
        for elements in result:
            l.append(elements['duration']['value'])
        # return list of duration
        return l


def get_params(origin_coord,
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
    url = "https://maps.googleapis.com/maps/api/distancematrix/json?"
    departure_time = "21/12/2022 18:00:00"

    origins_coord = [(48.8534951, 2.3483915)]
    origins_name = 'Paris'

    df_city = pd.read_csv('./Data/coord_city.csv')
    df_city = df_city.loc[df_city.city != origins_name]
    df_city.reset_index(inplace=True, drop=True)
    df_city['coord'] = list(zip(df_city.lat_city, df_city.lon_city))
    df_city['duration'] = -1

    i_ = 0
    for i in range(20, len(df_city), 20):
        d = df_city['coord'][i_:i]
        parameters = get_params(origins_coord, d, departure_time)
        df_city['duration'][i_:i] = execute_req(parameters)
        i_ = i
    if i_ < len(df_city) - 1:
        d = df_city['coord'][i_:len(df_city) - 1]
        parameters = get_params(origins_coord, d, departure_time)
        df_city['duration'][i_:len(df_city) - 1] = execute_req(parameters)

    df_city.to_csv(origins_name + '_' + 'time_veh.csv')
print(execute_req(get_params('Paris','Lyon')))