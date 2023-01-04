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
import folium
import time
import datetime
import calcul_distances as cdist

def time_api_teq(time):
    year= time[0:4]
    month = time[5:7]
    day = time[8:10]
    hour = time[11:13]
    min= time[14:16]
    time_format = datetime.datetime(int(year),int(month),int(day),int(hour),int(min))
    return(time_format)
        
def delta_time_api(time1,time2):
    time1_format = time_api_teq(time1)
    time2_format = time_api_teq(time2)
    delta = time2_format-time1_format
    return(delta)

def delta_time_dep(time):
    time_format = time_api_teq(time)
    delta = time_format-datetime.datetime.utcnow()
    return(delta)

def vol_dest_api(code):
    t=time.localtime()
    
    date_ajd = str(t.tm_mday)+'/'+str(t.tm_mon)+'/'+str(t.tm_year)
    date_plus3 =str(int(t.tm_mday)+3)+'/'+str(t.tm_mon)+'/'+str(t.tm_year)
    
    heure_mtn = str(t.tm_hour)+':'+str(t.tm_min)
    
    nombre_res =1000
    r=requests.get('https://api.tequila.kiwi.com/v2/search?fly_from='+ str(code) +'&dateFrom='+ date_ajd+'&dateTo='+date_plus3+'&dtime_from='+ heure_mtn,headers= {'apikey': 'heKrsP3At973_NDG5Rdo5Hxev6myEuDa', 'accept': 'application/json'})
    
    if r.status_code != 200: # see HTTP errors
        print("HTTP ERROR")
    else:  
        
        
        
        dest = pd.DataFrame(r.json()['data']) # make pandas dataframe from the JSON obtained through the API -- to adapt if format is not JSON

        airports = pd.read_csv('Data/ensemble_airports.csv')
        dest.rename(columns={'flyTo':'code'}, inplace= True)
        if not dest.empty:
            dest = pd.merge(dest,airports, on='code', how='left')
            
        else:
        
            print('Aucun vol au départ de '+ str(code) + '.')
        
      
        
    def temps_vol(x):
        return(delta_time_api(x['utc_departure'],x['utc_arrival']))
    def temps_depart(x):
        return(delta_time_dep(x['utc_arrival']))
    
    dest['Tps_trajet']= dest.apply(temps_vol,axis=1)
    dest['Tps_total'] =dest.apply(temps_depart,axis=1)
    
    def temps_vol_sec(x):
        temps_vol = str(x['Tps_trajet'])
        min=temps_vol[-5:-3]
        heure = temps_vol[-8:-6]
        return(60*int(min)+3600*int(heure))
    
    def temps_vol_dep_sec(x):
        temps_vol = str(x['Tps_total'])
        min=temps_vol[-12:-10]
        heure = temps_vol[-15:-13]
        return(60*int(min)+3600*int(heure))
    
    dest['Tps_trajet_sec']= dest.apply(temps_vol_sec,axis=1)
    dest['Tps_total_sec'] = dest.apply(temps_vol_dep_sec,axis=1)
    
    lon_ori = airports[airports['code']==code]['lon']
    lat_ori = airports[airports['code']==code]['lat']    
    
    def add_dist_df(x):
        return(round(cdist.get_dist_km_2(lon_ori,lat_ori,x['lon'],x['lat']),1))
        
    dest['Distance'] = dest.apply(add_dist_df,axis=1)
        
    return(dest)

def voldest_dureemax(code,minutes_max):
    dest = vol_dest_api(code)
    dest_dureemax = dest[dest['Tps_total_sec']<60*minutes_max]
    return(dest_dureemax)
    
    
def recherche_airport(nom_recherche):
    airports = pd.read_csv('Data/ensemble_airports.csv')
    airport_filtre= airports[airports['alternative_names'].str.contains(nom_recherche, na=False)]
    return(airport_filtre)
    
def affichage_vol_dest_code(code):
           #Affichage Folium
       
    airports = pd.read_csv('Data/ensemble_airports.csv')
    airports_dest=vol_dest_api(code)
    
    airport_ori = airports[airports['code']==str(code)]
    
    airport_ori_longitude = airport_ori['lon'].iloc[0]
    airport_ori_latitude = airport_ori['lat'].iloc[0]  

    


    

    fmap= folium.Map(location=[airport_ori_latitude,airport_ori_longitude])

    folium.Marker([airport_ori_latitude, airport_ori_longitude],
            popup=airport_ori['name'].iloc[0],
            icon=folium.Icon(color='green')).add_to(fmap)

    n = airports_dest.shape[0] #Nombre de gares

    for i in range(n):
        longitude = airports_dest['lon'].iloc[i]
        latitude = airports_dest['lat'].iloc[i]
        nom = airports_dest['cityTo'].iloc[i]
        distance = airports_dest['Distance'].iloc[i]
        Tps_trajet = airports_dest['Tps_trajet'].iloc[i]
        
        if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
            #Tracé du point
            folium.Marker([latitude, longitude],
            popup=nom +'\n Distance: ' + str(distance) + '\n Temps de trajet: ' ),
            icon=folium.Icon(color='red',icon='plane').add_to(fmap)
            
            #Tracé de la ligne
            points=[tuple([airport_ori_latitude,airport_ori_longitude]),tuple([latitude,longitude])]
            folium.PolyLine(points, color="red", weight=2.5, opacity=1).add_to(fmap)
    nom_fichier = 'Carte_vol_dest_'+ str(code) +'.html'
    fmap.save(outfile='Cartes/' + nom_fichier)

    
    
    fmap
    return(fmap)

def affichage_vol_dest(nom_recherche):
    
    
    ####Destinations en avion
    aeroports_recherche = recherche_airport(nom_recherche)
    
    
    nombre_aeroports = aeroports_recherche.shape[0]

    print(str(nombre_aeroports) + ' aéroport(s) trouvé(s) pour ' + str(nom_recherche) + '.')

    fmap= folium.Map(location=[45,0])
    couleur =['red','blue','green']
    for i in range(nombre_aeroports):
        
        code_aeroport = aeroports_recherche['code'].iloc[i]
        print('Recherche des destinations depuis ' + str(code_aeroport) +' (' + str(i+1) + '/' + str(nombre_aeroports) + ').' )
        airports_liste = pd.read_csv('Data/ensemble_airports.csv')
        airports_dest=vol_dest_api(code_aeroport)
        
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
                popup=nom +'\n Distance: ' + str(distance) + '\n Temps de trajet: ',
                icon=folium.Icon(color='red')).add_to(fmap)
                
                #Tracé de la ligne
                points=[tuple([airport_ori_latitude,airport_ori_longitude]),tuple([latitude,longitude])]
                folium.PolyLine(points, color=str(couleur[i]), weight=2.5, opacity=1).add_to(fmap)
        print('Fin de la recherche des destinations pour ' + str(code_aeroport) + '.')
        
        
        
    
    
    
    
    #Sortie    
    nom_fichier = 'Carte_vol_dest_'+ nom_recherche +'.html'
    fmap.save(outfile='Cartes/' + nom_fichier)
    return(fmap)

