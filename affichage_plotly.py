import plotly as plt
import pandas as pd
import affichage_vol_dest as avd


df = pd.read_csv('Data/ensemble_gares.csv')
garefr = df[df['lat']>35]
#fig = plt.plot(garefr, x="lon", y="lat",hover_name='name', title="A Plotly Express Figure",kind='scatter')

# If you print the figure, you'll see that it's just a regular figure with data and layout
# print(fig)

#fig.show()

def affichage_plotlty(nom_ville, minutes_max):
    
    #AVIONS
    
    aeroports_recherche = avd.recherche_airport(nom_ville)    
    nombre_aeroports = aeroports_recherche.shape[0]

    print(str(nombre_aeroports) + ' aéroport(s) trouvé(s) pour ' + str(nom_ville) + '.')
    dest = []
    couleur =['red','blue','green']
    
    for i in range(nombre_aeroports):
        
        code_aeroport = aeroports_recherche['code'].iloc[i]
        print('Recherche des destinations depuis ' + str(code_aeroport) +' (' + str(i+1) + '/' + str(nombre_aeroports) + ').' )
        airports_liste = pd.read_csv('Data/ensemble_airports.csv')
        airports_dest=avd.voldest_dureemax(code_aeroport,minutes_max=minutes_max)
        
        airport_ori = airports_liste[airports_liste['code']==str(code_aeroport)]
        
        airport_ori_longitude = airport_ori['lon'].iloc[0]
        airport_ori_latitude = airport_ori['lat'].iloc[0]  
        airports_dest['mode']='Avion'
        
        
        dest.append(pd.DataFrame(airports_dest))



            
        print('Fin de la recherche des destinations pour ' + str(code_aeroport) + '.')
        dest_aero = pd.concat(dest)
        
        
    #TRAIN
    
    trajets_train = pd.read_csv('Outputs/results_Bordeaux_20221213T135825.csv')
    
    

            
        return(dest_aero)

dest_aero = affichage_plotlty('Bordeaux',180)
fig = plt.plot(dest_aero, x="lon", y="lat",hover_name='cityTo', title="A Plotly Express Figure",kind='scatter')
fig.show()
