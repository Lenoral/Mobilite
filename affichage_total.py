###################################################
#
#Affichage des destination atteignables depuis une origine en train (20 prochains) ou en avion (journée)

#import affichage_vol_dest as avd
#import affichage_gare_sncf as ags
import calcul_distances as cdist
import folium
import pandas as pd

nom_recherche = 'Angoulême'
def affichage_total(nom_recherche):
    
    
    ####Destinations en avion
    aeroports_recherche = avd.recherche_airport(nom_recherche)
    gares_recherche = ags.recherche_gare(nom_recherche)
    
    nombre_aeroports = aeroports_recherche.shape[0]

    print(str(nombre_aeroports) + ' aéroport(s) trouvé(s) pour ' + str(nom_recherche) + '.')

    fmap= folium.Map(location=[45,0])
    couleur =['red','blue','green']
    for i in range(nombre_aeroports):
        
        code_aeroport = aeroports_recherche['code'].iloc[i]
        print('Recherche des destinations depuis ' + str(code_aeroport) +' (' + str(i+1) + '/' + str(nombre_aeroports) + ').' )
        airports_liste = pd.read_csv('Data/ensemble_airports.csv')
        airports_dest=avd.vol_dest_api(code_aeroport)
        
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
    
    gares_recherche= ags.requete_destinations_api(nom_recherche)
    if not gares_recherche.empty:
        
        gares_initiale_latitude = ags.recherche_gare(nom_recherche)['lat'].iloc[0]
        gares_initiale_longitude = ags.recherche_gare(nom_recherche)['lon'].iloc[0]


        departs_gares_latitude =gares_recherche["lat"]
        departs_gares_longitude = gares_recherche["lon"]


        folium.Marker([gares_initiale_latitude, gares_initiale_longitude],
                popup=gares_recherche['label'].iloc[0],
                icon=folium.Icon(color='green')).add_to(fmap)

        n = gares_recherche.shape[0] #Nombre de gares

        for i in range(n):
            longitude = departs_gares_longitude.iloc[i]
            latitude = departs_gares_latitude.iloc[i]
            nom = gares_recherche['label'].iloc[i]
            distance = gares_recherche['Distance'].iloc[i]
            horaire = gares_recherche['Horaire'].iloc[i]
            if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
                #Tracé du point
                folium.Marker([latitude, longitude],
                popup=nom + '\n Distance: ' + str(distance) + ' km' +'\n Départ: ' + horaire,
                icon=folium.Icon(color='blue')).add_to(fmap)
                
                #Tracé de la ligne
                points=[tuple([gares_initiale_latitude,gares_initiale_longitude]),tuple([latitude,longitude])]
                folium.PolyLine(points, color="blue", weight=2.5, opacity=1).add_to(fmap)
    
    
    
    
    #Sortie    
    nom_fichier = 'Carte_vol_dest_'+ nom_recherche +'.html'
    fmap.save(outfile='Cartes/' + nom_fichier)
    return(fmap)

#Affivhage totale dans les X prochaines heures.

def affichage_total_heures(nom_recherche,prochaines_heures):
    
    
    ####Destinations en avion
    aeroports_recherche = avd.recherche_airport(nom_recherche)
    gares_recherche = ags.recherche_gare(nom_recherche)
    
    nombre_aeroports = aeroports_recherche.shape[0]

    print(str(nombre_aeroports) + ' aéroport(s) trouvé(s) pour ' + str(nom_recherche) + '.')

    fmap= folium.Map(location=[45,0])
    couleur =['red','blue','green']
    for i in range(nombre_aeroports):
        
        code_aeroport = aeroports_recherche['code'].iloc[i]
        print('Recherche des destinations depuis ' + str(code_aeroport) +' (' + str(i+1) + '/' + str(nombre_aeroports) + ').' )
        airports_liste = pd.read_csv('Data/ensemble_airports.csv')
        airports_dest=avd.vol_dest_api(code_aeroport)
        
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
            nom = airports_dest['cityTo'].iloc[j]
            
            if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
                #Tracé du point
                folium.Marker([latitude, longitude],
                popup=nom ,
                icon=folium.Icon(color='red')).add_to(fmap)
                
                #Tracé de la ligne
                points=[tuple([airport_ori_latitude,airport_ori_longitude]),tuple([latitude,longitude])]
                folium.PolyLine(points, color=str(couleur[i]), weight=2.5, opacity=1).add_to(fmap)
        print('Fin de la recherche des destinations pour ' + str(code_aeroport) + '.')
        
        
        
    #Destination en train
    
    gares_recherche= ags.requete_destinations_api_cumul(nom_recherche,4)
    if not gares_recherche.empty:
        
        gares_initiale_latitude = ags.recherche_gare(nom_recherche)['lat'].iloc[0]
        gares_initiale_longitude = ags.recherche_gare(nom_recherche)['lon'].iloc[0]


        departs_gares_latitude =gares_recherche["lat"]
        departs_gares_longitude = gares_recherche["lon"]


        folium.Marker([gares_initiale_latitude, gares_initiale_longitude],
                popup=gares_recherche['label'].iloc[0],
                icon=folium.Icon(color='green')).add_to(fmap)

        n = gares_recherche.shape[0] #Nombre de gares

        for i in range(n):
            longitude = departs_gares_longitude.iloc[i]
            latitude = departs_gares_latitude.iloc[i]
            nom = gares_recherche['label'].iloc[i]
            distance = gares_recherche['Distance'].iloc[i]
            horaire = gares_recherche['Horaire'].iloc[i]
            if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
                #Tracé du point
                folium.Marker([latitude, longitude],
                popup=nom + '\n Distance: ' + str(distance) + ' km' +'\n Départ: ' + horaire,
                icon=folium.Icon(color='blue')).add_to(fmap)
                
                #Tracé de la ligne
                points=[tuple([gares_initiale_latitude,gares_initiale_longitude]),tuple([latitude,longitude])]
                folium.PolyLine(points, color="blue", weight=2.5, opacity=1).add_to(fmap)
    
    
    
    
    #Sortie    
    nom_fichier = 'Carte_vol_dest_'+ nom_recherche +'.html'
    fmap.save(outfile='Cartes/' + nom_fichier)
    return(fmap)

def affichage_total_df(dataframe):
    ##Couleurs
        
    ####Destinations en avion
    dest_avion = dataframe.loc[dataframe['mode']=='Avion']
    nbre_dest_avion = dest_avion.shape[0]

    fmap= folium.Map(location=[47,0])
        
    for vol in range(nbre_dest_avion):
        airport_ori = dest_avion['station_orig'].iloc[vol]
        airport_ori_latitude = dest_avion['lat_ori'].iloc[vol]
        airport_ori_longitude = dest_avion['lon_ori'].iloc[vol]
        longitude = dest_avion['lon'].iloc[vol]
        latitude = dest_avion['lat'].iloc[vol]
        nom = dest_avion['cityTo'].iloc[vol]
       
        if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
        #Tracé du point
            folium.Marker([latitude, longitude],
            popup=nom ,
            icon=folium.Icon(color='red')).add_to(fmap)
            
            #Tracé de la ligne
            points=[tuple([airport_ori_latitude,airport_ori_longitude]),tuple([latitude,longitude])]
            folium.PolyLine(points, color='red', weight=2.5, opacity=1).add_to(fmap)             



        folium.Marker([airport_ori_latitude, airport_ori_longitude],
                popup=str(airport_ori),
                icon=folium.Icon(color='green')).add_to(fmap)
####Destinations en train
    dest_train = dataframe.loc[dataframe['mode']=='Train']
    
    
   
    nbre_dest_train  = dest_train.shape[0]

    for train in range(nbre_dest_train):
        gare_ori = dest_train['station_orig'].iloc[train]
        gare_ori_latitude = dest_train['lat_ori'].iloc[train]
        gare_ori_longitude = dest_train['lon_ori'].iloc[train]
        longitude = dest_train['lon'].iloc[train]
        latitude = dest_train['lat'].iloc[train]
        nom = dest_train['cityTo'].iloc[train]
            
        if (not(pd.isna(latitude)) and not(pd.isna(longitude))):
        #Tracé du point
            folium.Marker([latitude, longitude],
            popup=nom ,
            icon=folium.Icon(color='blue')).add_to(fmap)
            
            #Tracé de la ligne
            points=[tuple([gare_ori_latitude,gare_ori_longitude]),tuple([latitude,longitude])]
            folium.PolyLine(points, color='blue', weight=2.5, opacity=1).add_to(fmap)             



        folium.Marker([gare_ori_latitude, gare_ori_longitude],
                popup=str(gare_ori),
                icon=folium.Icon(color='green')).add_to(fmap)
  
    
    
    
    
    #Sortie    
    nom_fichier = 'Carte_vol_dest_'+ nom_recherche +'.html'
    fmap.save(outfile='Cartes/' + nom_fichier)
    return(fmap)

