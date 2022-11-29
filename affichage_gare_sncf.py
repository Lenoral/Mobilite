###############################################################
#
# Fichier qui permet d'afficher les gares accessibles depuis une gare recherchée



##############################################################

#Importation des librairies & fichiers utilisés

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
import calcul_distances as cdist


#Acces aux données des gares SNCF

gares = pd.read_csv('Data/ensemble_gares.csv')

#Recherche des gares qui nous interessent

def recherche_gare(nom_gare):
    '''Renvoie les gares dont le nom contient nom_gare'''
    gares_filtres = gares[gares['name'].str.contains(nom_gare, na=False)]
    gares_filtres.insert(1,'SNCF_ID',gares_filtres['id'].str[15:])
    
    return(gares_filtres)

#Expression et lecture du temps en format API SNCF et standard

def time_api():
    '''Renvoie la date sous le format utilisé par l'api SNCF'''
    t = time.localtime()
    time_api= str(t.tm_year) + str(t.tm_mon) + str(t.tm_mday) + 'T' + str(t.tm_hour) + str(t.tm_min) + '1'
    
    return(time_api)

    
def time_standard(t):
    '''Converti le format temps de l'API SNCF en un format HH:MM  JJ/MM/AAAA'''
    year = t[0:4]
    month = t[4:6]
    day = t[6:8]
    hour= t[9:11]
    min = t[11:13]
    
    
    return(hour+ ':' + min + '  ' + day + '/' + month + '/' + year)


#Requete des 20 prochains trains au départ de la gare en question

def requete_destinations_api(nom_recherche):
    
    '''Renvoie le nom des destinations, et les coordonnées associées des 20 prochains départs de la gare recherchée'''
    
    gares_recherche = recherche_gare(nom_recherche) #Renvoie le dataframe des gares contenant le nom recherché
    if gares_recherche.empty:
        return('Aucune gare ne contient le nom recherché.')
    else:
        print('Les gares qui contiennent la recherche sont: ' + str(gares_recherche['label']))       

        SNCF_ID = gares_recherche['SNCF_ID'].iloc[0] #Selection de l'ID de la 1ere gare du tableau des gares recherchées

        print('Résultats présentés pour la gare '+ gares_recherche['label'].iloc[0] + ' (ID: ' + SNCF_ID +').') #Info utilisateurs de la gare choisie

        def page_departs(numero_page) :
            return requests.get(
                ('https://api.sncf.com/v1/coverage/sncf/stop_areas/stop_area:SNCF:'+SNCF_ID+'/departures?datetime=' + time_api()).format(numero_page),
                auth=('16cbfb01-1943-471f-aac9-7a1139abab77', ''))

        
        #On commence par la première page qui nous donne le nombre de résultats par page ainsi que le nombre total de résultats

        page_initiale = page_departs(0)
        item_per_page = page_initiale.json()['pagination']['items_per_page']
        total_items = page_initiale.json()['pagination']['total_result']
        departsdfs = []

        # on fait une boucle sur toutes les pages suivantes

        for page in range(int(total_items/item_per_page)+1) :
            departs_page = page_departs(page)

            ensemble_departs = departs_page.json()

            if 'departures' not in ensemble_departs:
                # pas d'arrêt
                continue

            # on ne retient que les informations qui nous intéressent
            for departs in ensemble_departs['departures']:

                departs['label'] = departs['display_informations']['direction']
        
                
            departs = ensemble_departs['departures']
            dp= pd.DataFrame(departs)

            departsdfs.append(dp)
        
            
        departs_liste = pd.concat(departsdfs)
        #Ajout des colonnes longitude et latitude dans le tableau des gares de destination 
        departs_gares = pd.merge(departs_liste,gares,on='label',how='left')
        departs_gares_loc= departs_gares[['label','lat','lon']]
        
        ###Coordonnées de la gare choisie (gare de départ)
        lat_ori = gares_recherche['lat'].iloc[0]
        lon_ori = gares_recherche['lon'].iloc[0]

        #Calcul de la distance entre la gare choisie et la gare de destination
        def add_dist_df(x):

            return(round(cdist.get_dist_km_2(lon_ori,lat_ori,x['lon'],x['lat']),1))
        
        departs_gares_loc['Distance'] = departs_gares_loc.apply(add_dist_df,axis=1)
        
        
        
    return(departs_gares_loc)    
    
####Affichage sur la carte des destination atteignables depuis la gare recherchée

def affichage_destination_map(nom_recherche):
    '''Affiche les destinations des 20 prochains trains au départs de la gare recherchée'''
    
    #Recherche des coordonnées de la gare choisie pour etre l'origine des trajets    
       
    gares_initiale_latitude = recherche_gare(nom_recherche)['lat'].iloc[0]
    gares_initiale_longitude = recherche_gare(nom_recherche)['lon'].iloc[0]
    
    #Recherche des destinations atteignable avec les 20 prochains trains au départ de la gare choisie
    
    gares_recherche=requete_destinations_api(nom_recherche)
    
    departs_gares_latitude =gares_recherche["lat"]
    departs_gares_longitude = gares_recherche["lon"]

    #Création de la carte, centrée sur la gare d'origine
    
    fmap= folium.Map(location=[departs_gares_latitude.iloc[0],departs_gares_longitude.iloc[0]])

    folium.Marker([gares_initiale_latitude, gares_initiale_longitude],
            popup=gares_recherche['label'].iloc[0],
            icon=folium.Icon(color='green')).add_to(fmap)

    n = gares_recherche.shape[0] #Nombre de gares de destination

    #Ajout des marqueurs et des lignes pour chaque destination
    
    for i in range(n):
        longitude = departs_gares_longitude.iloc[i]
        latitude = departs_gares_latitude.iloc[i]
        nom = gares_recherche['label'].iloc[i]
        distance = gares_recherche['Distance'].iloc[i]
        
        if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
            #Tracé du point
            folium.Marker([latitude, longitude],
            popup=nom + ' - ' + str(distance) + ' km',
            icon=folium.Icon(color='red')).add_to(fmap)
            
            #Tracé de la ligne
            points=[tuple([gares_initiale_latitude,gares_initiale_longitude]),tuple([latitude,longitude])]
            folium.PolyLine(points, color="red", weight=2.5, opacity=1).add_to(fmap)
    
    #Enregistrement du fichier        
            
    nom_fichier = 'Carte_SNCF_departs'+ str(recherche_gare(nom_recherche)['label'].iloc[0]) +'.html'
    fmap.save(outfile='Cartes/' + nom_fichier)

    return(fmap)

###Affichage des destinations, en modifiant la position des marqueurs sur la carte de telle façon que la distance
#entre la destination et l'origine soit proportionelle à un coefficient donné
        
def affichage_destination_map_h(nom_recherche):
    '''Affiche les destinations des 20 prochains trains au départs de la gare recherchée, en déformant les distances Origine/Destination'''
    
    #Recherche des coordonnées de la gare choisie pour etre l'origine des trajets       
    
    gares_initiale_latitude = recherche_gare(nom_recherche)['lat'].iloc[0]
    gares_initiale_longitude = recherche_gare(nom_recherche)['lon'].iloc[0]
    
    #Recherche des destinations atteignable avec les 20 prochains trains au départ de la gare choisie
    
    gares_recherche=requete_destinations_api(nom_recherche)

    departs_gares_latitude =gares_recherche["lat"]
    departs_gares_longitude = gares_recherche["lon"]

    #Création de la carte, centrée sur la gare d'origine
    
    fmap= folium.Map(location=[departs_gares_latitude.iloc[0],departs_gares_longitude.iloc[0]])

    folium.Marker([gares_initiale_latitude, gares_initiale_longitude],
            popup=gares_recherche['label'].iloc[0],
            icon=folium.Icon(color='green')).add_to(fmap)

    n = gares_recherche.shape[0] #Nombre de gares

    #Ajout des marqueurs et des lignes pour chaque destination
    
    for i in range(n):
        longitude = departs_gares_longitude.iloc[i]
        latitude = departs_gares_latitude.iloc[i]
        distance = gares_recherche['Distance'].iloc[i]
        new_coord= cdist.coord_homotethie(gares_initiale_longitude,gares_initiale_latitude,longitude,latitude,0.5) #Calcul de la nouvelle position déformée du marqueur
        nom = gares_recherche['label'].iloc[i]
        
        
        if (not(pd.isna(new_coord[1])) and not(pd.isna(new_coord[0]))):
            #Tracé du point
            folium.Marker([new_coord[1], new_coord[0]],
            popup=nom + ' - ' + str(distance) + ' km',
            icon=folium.Icon(color='red')).add_to(fmap)
            #Tracé de la ligne
            points=[tuple([gares_initiale_latitude,gares_initiale_longitude]),tuple([new_coord[1],new_coord[0]])]
            folium.PolyLine(points, color="blue", weight=2.5, opacity=1).add_to(fmap)
            
    #Enregistrement du fichier
            
    nom_fichier = 'Carte_SNCF_departs_h'+ str(recherche_gare(nom_recherche)['label'].iloc[0]) +'.html'
    fmap.save(outfile='Cartes/' + nom_fichier)

    return(fmap)

#Affichage des gares atteignables depuis une gare choisie via les 20 prochains trains, points réels et points déformés (combinaison des deux fonctions précédentes)

def affichage_destination_map_t(nom_recherche):
    '''Affiche les destinations des 20 prochains trains au départs de la gare recherchée'''
       
        
    gares_recherche=requete_destinations_api(nom_recherche)
    
    gares_initiale_latitude = recherche_gare(nom_recherche)['lat'].iloc[0]
    gares_initiale_longitude = recherche_gare(nom_recherche)['lon'].iloc[0]


    departs_gares_latitude =gares_recherche["lat"]
    departs_gares_longitude = gares_recherche["lon"]


    departs_gares_latitude.head()

    fmap= folium.Map(location=[departs_gares_latitude.iloc[0],departs_gares_longitude.iloc[0]])

    folium.Marker([gares_initiale_latitude, gares_initiale_longitude],
            popup=gares_recherche['label'].iloc[0],
            icon=folium.Icon(color='green')).add_to(fmap)

    n = gares_recherche.shape[0] #Nombre de gares
    
    for i in range(n):
        longitude = departs_gares_longitude.iloc[i]
        latitude = departs_gares_latitude.iloc[i]
        nom = gares_recherche['label'].iloc[i]
        distance = gares_recherche['Distance'].iloc[i]
        
        if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
            #Tracé du point
            folium.Marker([latitude, longitude],
            popup=nom + ' - ' + str(distance) + ' km',
            icon=folium.Icon(color='red')).add_to(fmap)
            
            #Tracé de la ligne
            points=[tuple([gares_initiale_latitude,gares_initiale_longitude]),tuple([latitude,longitude])]
            folium.PolyLine(points, color="red", weight=2.5, opacity=1).add_to(fmap)
    for i in range(n):
        longitude = departs_gares_longitude.iloc[i]
        latitude = departs_gares_latitude.iloc[i]
        distance = gares_recherche['Distance'].iloc[i]
        new_coord= cdist.coord_homotethie(gares_initiale_longitude,gares_initiale_latitude,longitude,latitude,0.5)
        nom = gares_recherche['label'].iloc[i]
        
        
        if (not(pd.isna(new_coord[1])) and not(pd.isna(new_coord[0]))):
            #Tracé du point
            folium.Marker([new_coord[1], new_coord[0]],
            popup=nom + ' - ' + str(distance) + ' km',
            icon=folium.Icon(color='blue')).add_to(fmap)
            #Tracé de la ligne
            points=[tuple([gares_initiale_latitude,gares_initiale_longitude]),tuple([new_coord[1],new_coord[0]])]
            folium.PolyLine(points, color="blue", weight=2.5, opacity=1).add_to(fmap)
            
            
    nom_fichier = 'Carte_SNCF_departs_t'+ str(recherche_gare(nom_recherche)['label'].iloc[0]) +'.html'
    fmap.save(outfile='Cartes/' + nom_fichier)


    return(fmap)
