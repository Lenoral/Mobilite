###################################################
#
#Affichage des destination atteignables depuis une origine en train (20 prochains) ou en avion (journée)

import affichage_vol_dest as avd
import calcul_distances as cdist
import folium
import pandas as pd
import os
import numpy as np
import io
import json
import scipy.spatial
import csv
from datetime import datetime
import time
import requests
import pickle
from requests.adapters import HTTPAdapter
import itertools  # list operators
import tqdm
import geopandas
from shapely.geometry import Polygon


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

def get_OD_now(ville_origine,nb_trajets,etranger,niveau_service,minutes_max):
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
        df_station = df_station.loc[df_station["Niveau de service"] >= niveau_service]
        df_station_foreign = pd.read_csv('./Data/gares_etrangeres.csv', usecols=['name', 'id', 'lat', 'lon', 'city'])

        # search OD and time
        '''==============================================TO SET=========================================================='''
        o = str(ville_origine)
        dt0= str(datetime.strftime(datetime.now(),'%d/%m/%Y %H:%M:%S'))
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
        if etranger:
            for city_d in d_e:
                df_city = []
                for station_d in df_station_foreign.loc[df_station_foreign['city'] == city_d].iterrows():
                    params = {'from': "admin:fr:" + get_cog(o, db_cog),
                            'to': station_d[1]['id'],
                            'datetime': str(t_string),
                            'min_nb_journeys': 0,
                            'max_nb_transfers': nb_trajets
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
        cols = list(results[d_city].columns)
        for city in results.keys():
            total_time[city] = results[city].loc[results[city]['duration'] == min(results[city]['duration'])].values.tolist()[0] # if several journeys with same duration, keep the first
        # the trip with min duration(in train and transfer) for each destination city not station
        total_time = pd.DataFrame.from_dict(total_time, orient='index', columns=cols)

        # save results
        results_df = pd.concat(results.values(), ignore_index=True)
        #results_df.to_csv('Outputs/trajets' + '_' + o + '_' + t_string + '.csv')
        with open('results_' + o + '.pickle', 'wb') as f:
            pickle.dump(results, f)
        
        
        result_limit =total_time[total_time['total_time']<60*minutes_max]
        #result_limit.to_csv('Outputs/results' + '_' + o + '_' + t_string + '.csv')
    return(result_limit)

def affichage_total(nom_recherche,minutes_max):
    
    
    ####Destinations en avion
    aeroports_recherche = avd.recherche_airport(nom_recherche)
    
    
    nombre_aeroports = aeroports_recherche.shape[0]

    print(str(nombre_aeroports) + ' aéroport(s) trouvé(s) pour ' + str(nom_recherche) + '.')

    fmap= folium.Map(location=[48,0])
    couleur =['red','blue','green']
    for i in range(nombre_aeroports):
        
        code_aeroport = aeroports_recherche['code'].iloc[i]
        print('Recherche des destinations depuis ' + str(code_aeroport) +' (' + str(i+1) + '/' + str(nombre_aeroports) + ').' )
        airports_liste = pd.read_csv('Data/ensemble_airports.csv')
        airports_dest=avd.voldest_dureemax(code_aeroport,minutes_max=minutes_max-60)
        
        airport_ori = airports_liste[airports_liste['code']==str(code_aeroport)]
        
        airport_ori_longitude = airport_ori['lon'].iloc[0]
        airport_ori_latitude = airport_ori['lat'].iloc[0]  

        



        folium.Marker([airport_ori_latitude, airport_ori_longitude],
                popup=airport_ori['name'].iloc[0],
                icon=folium.Icon(color='green')).add_to(fmap)

        n = airports_dest.shape[0] #Nombre de gares

        for j in range(n):
            longitude = airports_dest['lon'].iloc[j]
            latitude = airports_dest['lat'].iloc[j]
            nom = airports_dest['cityTo'].iloc[i]
            distance = airports_dest['Distance'].iloc[i]
            Tps_trajet = airports_dest['Tps_trajet'].iloc[i]
            
            
            if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
                #Tracé du point
                folium.Marker([latitude, longitude],
                popup=nom +'\n Distance: ' + str(distance) + '\n Temps de trajet: ' + str(Tps_trajet),
                icon=folium.Icon(color='red')).add_to(fmap)
                
                #Tracé de la ligne
                points=[tuple([airport_ori_latitude,airport_ori_longitude]),tuple([latitude,longitude])]
                folium.PolyLine(points, color=str(couleur[i]), weight=2.5, opacity=1).add_to(fmap)
        print('Fin de la recherche des destinations pour ' + str(code_aeroport) + '.')
        
        
        
    #Destination en train
    gares_recherche = get_OD_now(ville_origine=nom_recherche,nb_trajets=1,minutes_max=minutes_max,etranger=True,niveau_service=2)
    
    if not gares_recherche.empty:
    


        departs_gares_latitude = str(gares_recherche["station_orig_lat"].iloc[0])
        departs_gares_longitude = str(gares_recherche["station_orig_lon"].iloc[0])


        folium.Marker([departs_gares_latitude,  departs_gares_longitude],
                popup=str(gares_recherche['station_orig'].iloc[0]),
                icon=folium.Icon(color='green')).add_to(fmap)

        n = int(gares_recherche.shape[0]) #Nombre d'OD

        for i in range(n):
            longitude = str(gares_recherche['station_dest_lon'].iloc[i])
            latitude = str(gares_recherche['station_dest_lat'].iloc[i])
            nom = str(gares_recherche['station_dest'].iloc[i])
            #distance = gares_recherche['Distance'].iloc[i]
            horaire = str(gares_recherche['h_depart'].iloc[i])
            if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
                #Tracé du point
                folium.Marker([latitude, longitude],
                popup=nom + '\n Distance: ' + str('distance') + ' km' +'\n Départ: ' + str(horaire),
                icon=folium.Icon(color='blue')).add_to(fmap)
                
                #Tracé de la ligne
                Olat=float(gares_recherche['station_orig_lat'].iloc[i])
                points=[tuple([round(Olat,5),str(gares_recherche['station_orig_lon'].iloc[i])]), tuple([latitude,longitude])]
                folium.PolyLine(points, color="blue", weight=2.5, opacity=1).add_to(fmap)
    
    
    
    
    #Sortie    
    nom_fichier = 'Carte_vol_train_dest_'+ nom_recherche +'.html'
    fmap.save(outfile='Cartes/' + nom_fichier)
    return(fmap)

#Affivhage totale dans les X prochaines heures.



def affichage_total_gpd(nom_recherche,minutes_max_train, minutes_max_avion):
    
    
    ####Destinations en avion
    aeroports_recherche = avd.recherche_airport(nom_recherche)
    
    
    nombre_aeroports = aeroports_recherche.shape[0]

    print(str(nombre_aeroports) + ' aéroport(s) trouvé(s) pour ' + str(nom_recherche) + '.')

    fmap= folium.Map(location=[48,0])
    couleur =['red','red','red']
    destinations_aero = []
    for i in range(nombre_aeroports):
        
        code_aeroport = aeroports_recherche['code'].iloc[i]
        print('Recherche des destinations depuis ' + str(code_aeroport) +' (' + str(i+1) + '/' + str(nombre_aeroports) + ').' )
        airports_liste = pd.read_csv('Data/ensemble_airports.csv')
        airports_dest=avd.voldest_dureemax(code_aeroport,minutes_max=minutes_max_avion)
        
        airport_ori = airports_liste[airports_liste['code']==str(code_aeroport)]
        
        airport_ori_longitude = airport_ori['lon'].iloc[0]
        airport_ori_latitude = airport_ori['lat'].iloc[0]  

        



        folium.Marker([airport_ori_latitude, airport_ori_longitude],
                popup=airport_ori['name'].iloc[0],
                icon=folium.Icon(color='green')).add_to(fmap)

        n = airports_dest.shape[0] #Nombre de gares
        
        for j in range(n):
            longitude = airports_dest['lon'].iloc[j]
            latitude = airports_dest['lat'].iloc[j]
            nom = airports_dest['cityTo'].iloc[i]
            distance = airports_dest['Distance'].iloc[i]
            Tps_trajet = airports_dest['Tps_trajet'].iloc[i]
            
            
            if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
                destinations_aero.append([longitude,latitude])
                #Tracé du point
                folium.Marker([latitude, longitude],
                popup=nom +'\n Distance: ' + str(distance) + '\n Temps de trajet: ' + str(Tps_trajet),
                icon=folium.Icon(color='red')).add_to(fmap)
                
                #Tracé de la ligne
                points=[tuple([airport_ori_latitude,airport_ori_longitude]),tuple([latitude,longitude])]
                folium.PolyLine(points, color=str(couleur[i]), weight=2.5, opacity=1).add_to(fmap)
        print('Fin de la recherche des destinations pour ' + str(code_aeroport) + '.')
       
        
    #Destination en train
    
    
    #gares_recherche = pd.read_csv('Outputs/results_Bordeaux_20221213T135825.csv')

    gares_recherche = get_OD_now(ville_origine=nom_recherche,nb_trajets=1,minutes_max=minutes_max_train,etranger=True,niveau_service=2)
    
    if not gares_recherche.empty:
    


        departs_gares_latitude = str(gares_recherche["station_orig_lat"].iloc[0])
        departs_gares_longitude = str(gares_recherche["station_orig_lon"].iloc[0])


        folium.Marker([departs_gares_latitude,  departs_gares_longitude],
                popup=str(gares_recherche['station_orig'].iloc[0]),
                icon=folium.Icon(color='green')).add_to(fmap)

        n = int(gares_recherche.shape[0]) #Nombre d'OD
        destinations_train = []
        for i in range(n):
            longitude = str(gares_recherche['station_dest_lon'].iloc[i])
            latitude = str(gares_recherche['station_dest_lat'].iloc[i])
            nom = str(gares_recherche['station_dest'].iloc[i])
            #distance = gares_recherche['Distance'].iloc[i]
            horaire = str(gares_recherche['h_depart'].iloc[i])
            if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
                destinations_train.append([longitude,latitude])
                #Tracé du point
                folium.Marker([latitude, longitude],
                popup=nom + '\n Distance: ' + str('distance') + ' km' +'\n Départ: ' + str(horaire),
                icon=folium.Icon(color='blue')).add_to(fmap)
                
                #Tracé de la ligne
                Olat=float(gares_recherche['station_orig_lat'].iloc[i])
                points=[tuple([round(Olat,5),str(gares_recherche['station_orig_lon'].iloc[i])]), tuple([latitude,longitude])]
                folium.PolyLine(points, color="blue", weight=2.5, opacity=1).add_to(fmap)
    destinations_train.append([gares_recherche['station_orig_lon'].iloc[0],gares_recherche['station_orig_lat'].iloc[0]])
    destinations_aero.append([gares_recherche['station_orig_lon'].iloc[0],gares_recherche['station_orig_lat'].iloc[0]])
    hull_train = scipy.spatial.ConvexHull(destinations_train)
    point_hull_train = [hull_train.points[vertice] for vertice in hull_train.vertices]
    perim_train= Polygon(point_hull_train)
    def boundary_style_function_train(feature):
        return {'weight': 2, 'color': 'green' ,'fill':True}
        
    folium.GeoJson(data=perim_train, name='Accessibilité train', style_function = boundary_style_function_train).add_to(fmap)
    hull_aero = scipy.spatial.ConvexHull(destinations_aero)
    point_hull_aero = [hull_aero.points[vertice] for vertice in hull_aero.vertices]
    perim_aero = Polygon(point_hull_aero)
    def boundary_style_function_aero(feature):
        return {'weight': 2, 'color': 'red' ,'fill':True}
        
    folium.GeoJson(data=perim_aero, name='Accessibilité avion', style_function = boundary_style_function_aero).add_to(fmap)

    
    #Sortie    
    nom_fichier = 'Carte_vol_train_dest_'+ nom_recherche + '_A_' + str(minutes_max_avion) + '_T_' + str(minutes_max_train)+'.html'
    fmap.save(outfile='Cartes/' + nom_fichier)
    return(fmap)

def affichage_total_gpd_def(nom_recherche,minutes_max_train, minutes_max_avion):
    
    
    ####Destinations en avion
    aeroports_recherche = avd.recherche_airport(nom_recherche)
    
    
    nombre_aeroports = aeroports_recherche.shape[0]

    print(str(nombre_aeroports) + ' aéroport(s) trouvé(s) pour ' + str(nom_recherche) + '.')

    fmap= folium.Map(location=[48,0])
    couleur =['red','red','red']
    destinations_aero = []
    for i in range(nombre_aeroports):
        
        code_aeroport = aeroports_recherche['code'].iloc[i]
        print('Recherche des destinations depuis ' + str(code_aeroport) +' (' + str(i+1) + '/' + str(nombre_aeroports) + ').' )
        airports_liste = pd.read_csv('Data/ensemble_airports.csv')
        airports_dest=avd.voldest_dureemax(code_aeroport,minutes_max=minutes_max_avion)
        
        airport_ori = airports_liste[airports_liste['code']==str(code_aeroport)]
        
        airport_ori_longitude = airport_ori['lon'].iloc[0]
        airport_ori_latitude = airport_ori['lat'].iloc[0]  

        



        folium.Marker([airport_ori_latitude, airport_ori_longitude],
                popup=airport_ori['name'].iloc[0],
                icon=folium.Icon(color='green')).add_to(fmap)

        n = airports_dest.shape[0] #Nombre de gares
        
        for j in range(n):
            longitude = airports_dest['lon'].iloc[j]
            latitude = airports_dest['lat'].iloc[j]
            nom = airports_dest['cityTo'].iloc[i]
            distance = airports_dest['Distance'].iloc[i]
            Tps_trajet = airports_dest['Tps_trajet'].iloc[i]
            
            
            if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
                destinations_aero.append([longitude,latitude])
                #Tracé du point
                folium.Marker([latitude, longitude],
                popup=nom +'\n Distance: ' + str(distance) + '\n Temps de trajet: ' + str(Tps_trajet),
                icon=folium.Icon(color='red')).add_to(fmap)
                
                #Tracé de la ligne
                points=[tuple([airport_ori_latitude,airport_ori_longitude]),tuple([latitude,longitude])]
                folium.PolyLine(points, color=str(couleur[i]), weight=2.5, opacity=1).add_to(fmap)
        print('Fin de la recherche des destinations pour ' + str(code_aeroport) + '.')
       
        
    #Destination en train
    
    
    #gares_recherche = pd.read_csv('Outputs/results_Bordeaux_20221213T135825.csv')

    gares_recherche = get_OD_now(ville_origine=nom_recherche,nb_trajets=1,minutes_max=minutes_max_train,etranger=True,niveau_service=2)
    
    if not gares_recherche.empty:
    


        departs_gares_latitude = str(gares_recherche["station_orig_lat"].iloc[0])
        departs_gares_longitude = str(gares_recherche["station_orig_lon"].iloc[0])


        folium.Marker([departs_gares_latitude,  departs_gares_longitude],
                popup=str(gares_recherche['station_orig'].iloc[0]),
                icon=folium.Icon(color='green')).add_to(fmap)

        n = int(gares_recherche.shape[0]) #Nombre d'OD
        destinations_train = []
        for i in range(n):
            longitude = str(gares_recherche['station_dest_lon'].iloc[i])
            latitude = str(gares_recherche['station_dest_lat'].iloc[i])
            nom = str(gares_recherche['station_dest'].iloc[i])
            #distance = gares_recherche['Distance'].iloc[i]
            horaire = str(gares_recherche['h_depart'].iloc[i])
            if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
                destinations_train.append([longitude,latitude])
                #Tracé du point
                folium.Marker([latitude, longitude],
                popup=nom + '\n Distance: ' + str('distance') + ' km' +'\n Départ: ' + str(horaire),
                icon=folium.Icon(color='blue')).add_to(fmap)
                
                #Tracé de la ligne
                Olat=float(gares_recherche['station_orig_lat'].iloc[i])
                points=[tuple([round(Olat,5),str(gares_recherche['station_orig_lon'].iloc[i])]), tuple([latitude,longitude])]
                folium.PolyLine(points, color="blue", weight=2.5, opacity=1).add_to(fmap)
    destinations_train.append([gares_recherche['station_orig_lon'].iloc[0],gares_recherche['station_orig_lat'].iloc[0]])
    destinations_aero.append([gares_recherche['station_orig_lon'].iloc[0],gares_recherche['station_orig_lat'].iloc[0]])
    hull_train = scipy.spatial.ConvexHull(destinations_train)
    point_hull_train = [hull_train.points[vertice] for vertice in hull_train.vertices]
    perim_train= Polygon(point_hull_train)
    def boundary_style_function_train(feature):
        return {'weight': 2, 'color': 'green' ,'fill':True}
        
    folium.GeoJson(data=perim_train, name='Accessibilité train', style_function = boundary_style_function_train).add_to(fmap)
    hull_aero = scipy.spatial.ConvexHull(destinations_aero)
    point_hull_aero = [hull_aero.points[vertice] for vertice in hull_aero.vertices]
    perim_aero = Polygon(point_hull_aero)
    def boundary_style_function_aero(feature):
        return {'weight': 2, 'color': 'red' ,'fill':True}
        
    folium.GeoJson(data=perim_aero, name='Accessibilité avion', style_function = boundary_style_function_aero).add_to(fmap)

    
    #Sortie    
    nom_fichier = 'Carte_vol_train_dest_'+ nom_recherche +'.html'
    fmap.save(outfile='Cartes/' + nom_fichier)
    return(fmap)

affichage_total_gpd('Bordeaux', 1440,1440)