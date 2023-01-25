import plotly as plt
import pandas as pd
import affichage_vol_dest as avd
import calcul_distances as cdist
import get_journey_sncf_now as gjn
from math import *
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pytz
import json
from datetime import datetime
import requests
#fig = plt.plot(garefr, x="lon", y="lat",hover_name='name', title="A Plotly Express Figure",kind='scatter')

# If you print the figure, you'll see that it's just a regular figure with data and layout
# print(fig)

#fig.show()

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


def get_params_google(origin,
               dest,
               departure_time=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
               zone='Europe/Paris',
               mode="driving",
               traffic_mode="best_guess",
               key='AIzaSyDxAF6tBpC7b_gDEf2cQth-weR9schPZ-o'):
    tz = pytz.timezone(zone)
    dt_strp = tz.localize(datetime.strptime(departure_time, '%d/%m/%Y %H:%M:%S'))
    dt_utc = dt_strp.astimezone(pytz.UTC)
    timestamp = int(dt_utc.timestamp())
    param = {"origins": origin,
             "destinations": dest,
             "departure_time": timestamp,
             "mode": mode,
             "traffic_mode": traffic_mode,
             "language": "fr-FR",
             "key": key}
    return param

def affichage_plotlty(nom_ville, minutes_max):
    
    #AVIONS
    
    aeroports_recherche = avd.recherche_airport(nom_ville)    
    nombre_aeroports = aeroports_recherche.shape[0]
    airports = pd.read_csv('Data/ensemble_airports.csv')
    print(str(nombre_aeroports) + ' aéroport(s) trouvé(s) pour ' + str(nom_ville) + '.')
    dest = []
    
    for i in range(nombre_aeroports):
        nom_aeroport = aeroports_recherche['name'].iloc[i]
        code_aeroport = aeroports_recherche['code'].iloc[i]
        print('Recherche des destinations depuis ' + str(code_aeroport) +' (' + str(i+1) + '/' + str(nombre_aeroports) + ').' )
        airports_liste = pd.read_csv('Data/ensemble_airports.csv')
        airports_dest=avd.voldest_dureemax(code_aeroport,minutes_max=minutes_max)
        
        airport_ori = airports_liste[airports_liste['code']==str(code_aeroport)]
        
        airport_ori_longitude = airport_ori['lon'].iloc[0]
        airport_ori_latitude = airport_ori['lat'].iloc[0]  
        airports_dest['mode']='Avion'
        airports_dest['lat_ori']=airport_ori_latitude
        airports_dest['lon_ori']=airport_ori_longitude
        airports_dest['station_orig']=nom_aeroport
        airports_dest['station_dest']='0'
        def nom_aeroport_arrivee(x):
            return(str(airports['name'].loc[airports['code']==str(x['cityCodeTo'])].iloc[0]))
        for j in range (airports_dest.shape[0]):
            try:
                station_dest = airports['name'].loc[airports['code']==airports_dest['cityCodeTo'].iloc[j]].iloc[0]
            except (IndexError):
                airports_dest['station_dest'].loc[j]= airports_dest['cityTo'].iloc[j]
            else:
                airports_dest['station_dest'].loc[j]=station_dest
        #Ajout des durées voitures pour les vols
    
        dest.append(pd.DataFrame(airports_dest))



            
        print('Fin de la recherche des destinations pour ' + str(code_aeroport) + '.')
        dest_aero = pd.concat(dest)
        
        dest_aero.drop_duplicates(subset='cityTo',keep='first',inplace=True)
        
        
        
    #TRAIN
    trajets_train= gjn.get_OD_now(nom_ville,nb_trajets=2,minutes_max=1500,etranger=False,niveau_service=2)
    #trajets_train = pd.read_csv('Outputs/trajets_Bordeaux_20230123T150448.csv')
    trajets_train_copy = trajets_train.copy()
    trajets_train_copy['mode']='Train'

    def calcul_tps_trajet(x):
        return(x['total_time']-x['waiting_time'])

    trajets_train_copy['Tps_trajet_sec'] = trajets_train_copy.apply(calcul_tps_trajet,axis=1)

    lat_ori = trajets_train_copy['station_orig_lat'].iloc[0]
    lon_ori = trajets_train_copy['station_orig_lon'].iloc[0]


    def add_dist_df(x):
        return(round(cdist.get_dist_km_2(lon_ori,lat_ori,x['station_dest_lon'],x['station_dest_lat']),1))

    trajets_train_copy['Distance']=trajets_train_copy.apply(add_dist_df, axis=1)
    
    trajets_train_reduit = trajets_train_copy[['depart','station_orig_lat','station_orig_lon','arrival','station_dest_lat','station_dest_lon','station_orig','station_dest','Tps_trajet_sec','total_time','Distance','mode']]

    new_names = {'depart':'cityFrom',
                'station_orig_lat':'lat_ori',
                'station_orig_lon':'lon_ori',
                'arrival':'cityTo',
                'station_dest_lat':'lat',
                'station_dest_lon':'lon',
                'total_time':'Tps_total_sec'
                }
    trajets_train_reduit.rename(columns = new_names,inplace=True)
    
    
    #Agglomeration des trajets train et avion
    
    
    dest_aero_copy = dest_aero.copy()
    dest_aero_reduit= dest_aero_copy[['cityFrom','lat_ori','lon_ori','cityTo','lat','lon','station_orig','station_dest','Tps_trajet_sec','Tps_total_sec','mode','Distance']]
    dest_reduit_total = dest_aero_reduit.append(trajets_train_reduit)
    dest_reduit_total.loc[len(dest_reduit_total)]=[nom_ville,lat_ori,lon_ori,nom_ville,lat_ori,lon_ori,nom_ville,nom_ville,0,0,'Origine',0]    


    nbre_dest_avion = dest_reduit_total[dest_reduit_total['mode']=='Avion'].shape[0]
    nbre_dest_train = dest_reduit_total[dest_reduit_total['mode']=='Train'].shape[0]

    print(str(nbre_dest_avion) + " destinations en avion.")
    print(str(nbre_dest_train) + " destinations en train.")

    #Ajout des trahets en voiture
    n_pro=dest_reduit_total.shape[0]
    for i in range(n_pro):
        lat_ori = dest_reduit_total['lat_ori'].iloc[i]
        lon_ori = dest_reduit_total['lon_ori'].iloc[i]
        lat = dest_reduit_total['lat'].iloc[i]
        lon = dest_reduit_total['lon'].iloc[i]
        distance = dest_reduit_total['Distance'].iloc[i]
        ville_depart = dest_reduit_total['cityFrom'].iloc[i]
        ville_arrivee = dest_reduit_total['cityTo'].iloc[i]
        print("d "+ville_depart+ "(" +str(i)+ "/" + str(n_pro)+")")
        print("a " + ville_arrivee)
        try:
            Tps_trajet_voiture = execute_req_google(get_params_google(ville_depart,ville_arrivee))
        except (KeyError,IndexError):   
            a=0
        else:
            dest_reduit_total.loc[len(dest_reduit_total)]=[nom_ville,lat_ori,lon_ori,ville_arrivee,lat,lon,ville_depart,ville_arrivee,Tps_trajet_voiture,Tps_trajet_voiture,'Voiture',distance]
        
    dest_reduit_total['Tps_transit_aller']=0
    dest_reduit_total['Tps_transit_retour']=0
    #Calcul des temps de transit
    
    iter = 0
    for trajets_avion in range(nbre_dest_avion):
        iter+=1
        lat_ori = dest_reduit_total['lat_ori'].iloc[trajets_avion]
        lon_ori = dest_reduit_total['lon_ori'].iloc[trajets_avion]
        lat = dest_reduit_total['lat'].iloc[trajets_avion]
        lon = dest_reduit_total['lon'].iloc[trajets_avion]
        distance = dest_reduit_total['Distance'].iloc[trajets_avion]
        
        ville_depart = dest_reduit_total['cityFrom'].iloc[trajets_avion]
        ville_arrivee = dest_reduit_total['cityTo'].iloc[trajets_avion]
            
        station_dest_nom = dest_reduit_total[dest_reduit_total['mode']=='Avion']['station_dest'].iloc[trajets_avion]
        station_orig_nom = dest_reduit_total[dest_reduit_total['mode']=='Avion']['station_orig'].iloc[trajets_avion]
       
        Tps_trajet_sec= dest_reduit_total[dest_reduit_total['mode']=='Avion']['Tps_trajet_sec'].iloc[trajets_avion]
        Tps_total_sec= dest_reduit_total[dest_reduit_total['mode']=='Avion']['Tps_total_sec'].iloc[trajets_avion]
        
        cityFrom= dest_reduit_total[dest_reduit_total['mode']=='Avion']['cityFrom'].iloc[trajets_avion]
        cityTo=dest_reduit_total[dest_reduit_total['mode']=='Avion']['cityTo'].iloc[trajets_avion]
         
        if station_dest_nom==cityTo:
            station_dest_nom = str(station_dest_nom) + " Airport"
            print(station_dest_nom)
        if station_orig_nom==cityFrom:
            station_orig_nom = str(station_orig_nom) + " Airport"
            print(station_orig_nom)
        
        try :
            Tps_transit_aller = execute_req_google(get_params_google(cityFrom,station_orig_nom))
        except(KeyError,IndexError):
            Tps_transit_aller=-1
            print("error aller " + str(cityFrom) + " / " + str(station_orig_nom))
            
        else:
            a=0    
           
        try:
            Tps_transit_retour = execute_req_google(get_params_google(station_dest_nom,cityTo))
        except(KeyError,IndexError):
            Tps_transit_retour = -1
            print("error retour " + str(station_dest_nom) + " / " + str(cityTo))
        else:
            a=0
            
            
        dest_reduit_total.loc[len(dest_reduit_total)]=[nom_ville,lat_ori,lon_ori,ville_arrivee,lat,lon,station_orig_nom,station_dest_nom,Tps_trajet_sec,Tps_total_sec,'Avion',distance,Tps_transit_aller,Tps_transit_retour]
        
        print("Calcul des temps de transit Avion "+ str(trajets_avion+1) +"/"+ str(nbre_dest_avion)+".")

        
        iter = 0
    for trajets_train in range(nbre_dest_train):
        iter+=1
        lat_ori = dest_reduit_total['lat_ori'].iloc[trajets_train]
        lon_ori = dest_reduit_total['lon_ori'].iloc[trajets_train]
        lat = dest_reduit_total['lat'].iloc[trajets_train]
        lon = dest_reduit_total['lon'].iloc[trajets_train]
        distance = dest_reduit_total['Distance'].iloc[trajets_train]
        
        ville_depart = dest_reduit_total['cityFrom'].iloc[trajets_train]
        ville_arrivee = dest_reduit_total['cityTo'].iloc[trajets_train]
            
        station_dest_nom = dest_reduit_total[dest_reduit_total['mode']=='Train']['station_dest'].iloc[trajets_train]
        station_orig_nom = dest_reduit_total[dest_reduit_total['mode']=='Train']['station_orig'].iloc[trajets_train]
       
        Tps_trajet_sec= dest_reduit_total[dest_reduit_total['mode']=='Train']['Tps_trajet_sec'].iloc[trajets_train]
        Tps_total_sec= dest_reduit_total[dest_reduit_total['mode']=='Train']['Tps_total_sec'].iloc[trajets_train]
        
        cityFrom= dest_reduit_total[dest_reduit_total['mode']=='Train']['cityFrom'].iloc[trajets_train]
        cityTo=dest_reduit_total[dest_reduit_total['mode']=='Train']['cityTo'].iloc[trajets_train]
         
        if station_dest_nom==cityTo:
            station_dest_nom = str(station_dest_nom) + " Train Station"
            print(station_dest_nom)
        if station_orig_nom==cityFrom:
            station_orig_nom = str(station_orig_nom) + " Train Station"
            print(station_orig_nom)
        
        try :
            Tps_transit_aller = execute_req_google(get_params_google(cityFrom,station_orig_nom))
        except(KeyError,IndexError):
            Tps_transit_aller=-1
            print("error aller " + str(cityFrom) + " / " + str(station_orig_nom))
            
        else:
            a=0    
           
        try:
            Tps_transit_retour = execute_req_google(get_params_google(station_dest_nom,cityTo))
        except(KeyError,IndexError):
            Tps_transit_retour = -1
            print("error retour " + str(station_dest_nom) + " / " + str(cityTo))
        else:
            a=0
            
            
        dest_reduit_total.loc[len(dest_reduit_total)]=[nom_ville,lat_ori,lon_ori,ville_arrivee,lat,lon,station_orig_nom,station_dest_nom,Tps_trajet_sec,Tps_total_sec,'Train',distance,Tps_transit_aller,Tps_transit_retour]
        
        
        print("Calcul des temps de transit Train "+ str(trajets_train+1) +"/"+ str(nbre_dest_train)+".")
    #Calcul du trajet total
    
    def trajet_total_transit(x):
        return(x['Tps_transit_aller']+x['Tps_transit_retour'])
    
    dest_reduit_total['Tps_total_transit'] = dest_reduit_total.apply(trajet_total_transit,axis=1)

    
    def tps_total_avec_transit(x):
        return(x['Tps_trajet_sec']+x['Tps_total_transit'])
    
    dest_reduit_total['Tps_total_avec_transit']=dest_reduit_total.apply(tps_total_avec_transit,axis=1)
    
    #Calcul des coordonnées centrées
    
    def lat_centre_ori(x):
        return(float(x['lat'])-float(x['lat_ori']))
    def lon_centre_ori(x):
        return(float(x['lon'])-float(x['lon_ori']))

    dest_reduit_total['lat_dest_centre'] = dest_reduit_total.apply(lat_centre_ori,axis=1)
    dest_reduit_total['lon_dest_centre'] = dest_reduit_total.apply(lon_centre_ori,axis=1)
    
    
    if True:
        def lat_prop_tps(x):
            lat = x['lat_dest_centre']
            lon = x['lon_dest_centre']
            if not lon==0:
                angle = abs(atan(x['lat_dest_centre']/x['lon_dest_centre']))
                if lat>0:
                    if lon>0:
                        return(int(sin(angle)*x['Tps_total_avec_transit']/60))
                    else:
                        return(int(sin(angle)*x['Tps_total_avec_transit']/60))
                else:
                    if lon>0:
                        return((-1)*sin(angle)*x['Tps_total_avec_transit']/60)
                    else:
                        return((-1)*sin(angle)*x['Tps_total_avec_transit']/60)                   
            
            
            else:
                return(0)
            
        def lon_prop_tps(x):
            lat = x['lat_dest_centre']
            lon = x['lon_dest_centre']
            if not lon==0:
                angle = (atan(x['lat_dest_centre']/x['lon_dest_centre']))
                if lat>0:
                    if lon>0:
                        return(cos(angle)*x['Tps_total_avec_transit']/60)
                    else:
                        return((-1)*cos(angle)*x['Tps_total_avec_transit']/60)
                else:
                    if lon>0:
                        return(cos(angle)*x['Tps_total_avec_transit']/60)
                    else:
                        return((-1)*cos(angle)*x['Tps_total_avec_transit']/60)
                    
            
            
            else:
                return(0)    


    dest_reduit_total['lat_prop_tps']=dest_reduit_total.apply(lat_prop_tps,axis=1)
    dest_reduit_total['lon_prop_tps']=dest_reduit_total.apply(lon_prop_tps,axis=1)
        
   


    return(dest_reduit_total)



nom_ville = 'Paris'


#dest_reduit_total = affichage_plotlty(nom_ville,1400)


def affichage_classique(data):
    fig = plt.plot(data, x="lon_prop_tps", y="lat_prop_tps",hover_name='cityTo', color='mode',title="Destinations depuis Bordeaux",kind='scatter')
    fig.add_shape(type="circle",
    xref="x", yref="y",
    x0=-60, y0=-60, x1=60, y1=60,
    line_color="LightGreen",)
    fig.add_shape(type="circle",
    xref="x", yref="y",
    x0=-120, y0=-120, x1=120, y1=120,
    line_color="Green",)
    fig.add_shape(type="circle",
    xref="x", yref="y",
    x0=-180, y0=-180, x1=180, y1=180,
    line_color="LightSeaGreen",)
    fig.add_shape(type="circle",
    xref="x", yref="y",
    x0=-240, y0=-240, x1=240, y1=240,
    line_color="Blue",)
    fig.add_shape(type="circle",
    xref="x", yref="y",
    x0=-300, y0=-300, x1=300, y1=300,
    line_color="DarkBlue",)
    fig.add_shape(type="circle",
    xref="x", yref="y",
    x0=-360, y0=-360, x1=360, y1=360,
    line_color="Purple",)
    fig.add_shape(type="circle",
    xref="x", yref="y",
    x0=-720, y0=-720, x1=720, y1=720,
    line_color="Red",)
    
    fig.add_trace(go.Scatter(
        x=[0, 0,0,0,0,0,0],
        y=[40, 90,150,220,280,340,700],
        text=["-1h", "-2h","-3h","-4h","-5h","-6h","-12h"],
        mode="text",))
    
    fig.update_layout(
    autosize=True,
    width=1600,
    height=1200,
    margin=dict(
        l=50,
        r=50,
        b=50,
        t=50,
        pad=5
    ),
    
    
)
    
    fig.show()
    return()

def affichage_dynamique():


    app = Dash(__name__)


    app.layout = html.Div([
        html.H4('Interactive scatter plot with Iris dataset'),
        dcc.Graph(id="scatter-plot"),
        html.P("Filter by petal width:"),
        dcc.RangeSlider(
            id='range-slider',
            min=-2000, max=2000, step=5,
            marks={-2000: '-2000', 2000: '2000'},
            value=[-2000, 2000]
        ),
    ])


    @app.callback(
        Output("scatter-plot", "figure"), 
        Input("range-slider", "value"))
    def update_bar_chart(slider_range):
        df = dest_reduit_total # replace with your own data source
        low, high = slider_range
        mask = (df['Tps_total_sec'] > low) & (df['Tps_total_sec'] < high)
        fig = px.scatter(
            df[mask], x="lat_prop_tps", y="lon_prop_tps", 
            color="mode", 
            hover_data=['cityTo'])
        return fig


    app.run_server(debug=True)
    return()

