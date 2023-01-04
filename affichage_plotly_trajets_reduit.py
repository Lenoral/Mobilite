import plotly as plt
import pandas as pd
import affichage_vol_dest as avd
import calcul_distances as cdist
import get_journey_sncf_now as gjn
from math import *
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
#fig = plt.plot(garefr, x="lon", y="lat",hover_name='name', title="A Plotly Express Figure",kind='scatter')
villes_choisies= ['Quimper','Brest','Calais','Lille','Strasbourg','Lyon', 'Nice','Toulon','Marseille','Montpellier','Perpignan','Toulouse','Biarritz','Bayonne','Bordeaux','Nantes','Paris']
# If you print the figure, you'll see that it's just a regular figure with data and layout
# print(fig)

#fig.show()

def affichage_plotlty(nom_ville, minutes_max):
    
    #AVIONS
    
    aeroports_recherche = avd.recherche_airport(nom_ville)    
    nombre_aeroports = aeroports_recherche.shape[0]

    print(str(nombre_aeroports) + ' aéroport(s) trouvé(s) pour ' + str(nom_ville) + '.')
    dest = []
    
    for i in range(nombre_aeroports):
        
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
        
        dest.append(pd.DataFrame(airports_dest))



            
        print('Fin de la recherche des destinations pour ' + str(code_aeroport) + '.')
        dest_aero = pd.concat(dest)
        
        dest_aero.drop_duplicates(subset='cityTo',keep='first',inplace=True)
        
        
        
    #TRAIN
    trajets_train= gjn.get_OD_now(nom_ville,nb_trajets=3,minutes_max=8000,etranger=True,niveau_service=2)
    #trajets_train = pd.read_csv('Outputs/trajets_Lyon_20230104T140738.csv')
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

    trajets_train_reduit = trajets_train_copy[['depart','station_orig_lat','station_orig_lon','arrival','station_dest_lat','station_dest_lon','Tps_trajet_sec','total_time','Distance','mode']]

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
    dest_aero_reduit= dest_aero_copy[['cityFrom','lat_ori','lon_ori','cityTo','lat','lon','Tps_total_sec','Tps_trajet_sec','mode','Distance']]
    dest_reduit_total = dest_aero_reduit.append(trajets_train_reduit)
    dest_reduit_total.loc[len(dest_reduit_total)]=[nom_ville,lat_ori,lon_ori,nom_ville,lat_ori,lon_ori,0,0,'Origine',0]    

    
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
                        return(int(sin(angle)*x['Tps_trajet_sec']/60))
                    else:
                        return(int(sin(angle)*x['Tps_trajet_sec']/60))
                else:
                    if lon>0:
                        return((-1)*sin(angle)*x['Tps_trajet_sec']/60)
                    else:
                        return((-1)*sin(angle)*x['Tps_trajet_sec']/60)                   
            
            
            else:
                return(0)
            
        def lon_prop_tps(x):
            lat = x['lat_dest_centre']
            lon = x['lon_dest_centre']
            if not lon==0:
                angle = (atan(x['lat_dest_centre']/x['lon_dest_centre']))
                if lat>0:
                    if lon>0:
                        return(cos(angle)*x['Tps_trajet_sec']/60)
                    else:
                        return((-1)*cos(angle)*x['Tps_trajet_sec']/60)
                else:
                    if lon>0:
                        return(cos(angle)*x['Tps_trajet_sec']/60)
                    else:
                        return((-1)*cos(angle)*x['Tps_trajet_sec']/60)
                    
            
            
            else:
                return(0)    


    dest_reduit_total['lat_prop_tps']=dest_reduit_total.apply(lat_prop_tps,axis=1)
    dest_reduit_total['lon_prop_tps']=dest_reduit_total.apply(lon_prop_tps,axis=1)
        
    
    dest_reduit_total.reset_index()
    
    dest_reduit_total_red = dest_reduit_total.loc[dest_reduit_total['cityTo'].isin(villes_choisies)]
    
    return(dest_reduit_total_red)


if True:
    nom_ville = 'Lyon'

    dest_reduit_total = affichage_plotlty(nom_ville,8000)

    def affichage_classique():
        titre = "Carte de l'accessibilité depuis " + nom_ville
        fig = plt.plot(dest_reduit_total, x="lon_prop_tps", y="lat_prop_tps",hover_name='cityTo', color='mode',title=titre,kind='scatter',text="cityTo")
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
        x0=-540, y0=-540, x1=540, y1=540,
        line_color="Red",)
        
        fig.add_trace(go.Scatter(
            x=[0, 0,0,0,0,0,0],
            y=[40, 90,150,220,280,340,520],
            text=["-1h", "-2h","-3h","-4h","-5h","-6h","-9h"],
            mode="text",))
        fig.update_traces(textposition= 'top center')

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

    
    def affichage_classique_contours():
        lat_train = []
        lon_train = []
        
        for ville in villes_choisies:                
            if ville != 'Paris':
                info_ville = dest_reduit_total.loc[(dest_reduit_total['cityTo'] == ville) & (dest_reduit_total['mode'].isin(['Train','Origine']))]
                if not info_ville.empty:
                    lat_ville = info_ville['lat_prop_tps'].iloc[0]
                    lon_ville = info_ville['lon_prop_tps'].iloc[0]
                    lat_train.append(lat_ville)
                    lon_train.append(lon_ville)
                
        lat_avion = []
        lon_avion = []
        
        for ville in villes_choisies:
            if ville != 'Paris':
                info_ville = dest_reduit_total.loc[(dest_reduit_total['cityTo'] == ville) & (dest_reduit_total['mode'].isin(['Avion','Origine']))]
                if not info_ville.empty:
                    lat_ville = info_ville['lat_prop_tps'].iloc[0]
                    lon_ville = info_ville['lon_prop_tps'].iloc[0]
                    lat_avion.append(lat_ville)
                    lon_avion.append(lon_ville)
                
                        
        
        titre = "Carte de l'accessibilité depuis "+ nom_ville
        
        fig = plt.plot(dest_reduit_total, x="lon_prop_tps", y="lat_prop_tps",hover_name='cityTo', color='mode',title=titre,kind='scatter',text="cityTo")
        fig.add_scatter(x=lon_avion,y=lat_avion,fill="toself")
        fig.add_scatter(x=lon_train,y=lat_train,fill="toself")
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
        x0=-540, y0=-540, x1=540, y1=540,
        line_color="Red",)
        
        fig.add_trace(go.Scatter(
            x=[0, 0,0,0,0,0,0],
            y=[40, 90,150,220,280,340,520],
            text=["-1h", "-2h","-3h","-4h","-5h","-6h","-9h"],
            mode="text",))
        fig.update_traces(textposition= 'top center')
        
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
    
    
    affichage_classique_contours()
