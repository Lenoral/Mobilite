#Train stations

import pandas as pd
import matplotlib.pyplot as plt

gares = pd.read_csv("train_stations_europe.csv")

#Gares de France

def affichage_gares_france():
    gares_france= gares[gares["country"]=='FR']

    gares_france_latitude =gares_france["latitude"]
    gares_france_longitude = gares_france["longitude"]

    plt.scatter(gares_france_longitude,gares_france_latitude, color="red")
    plt.show()
    return()

#Gares de UK


def affichage_gares_europe():
    
    gares_latitude =gares["latitude"]
    gares_longitude = gares["longitude"]

    plt.scatter(gares_longitude,gares_latitude, color="green")
    plt.show()
    return()

def affichage_gares_pays(code_pays):
    
    gares_pays= gares[gares["country"]==code_pays]

    gares_pays_latitude =gares_pays["latitude"]
    gares_pays_longitude = gares_pays["longitude"]

    plt.scatter(gares_pays_longitude,gares_pays_latitude, color="orange")
    plt.show()
    return()

#Affichage des gares d'un pays particulier

code_pays="GB" #France =FR, Allemagne = DE, grande Bretagne = GB, etc.

affichage_gares_pays(code_pays) 