# Crée un fichier check_columns.py à la racine et lance-le
import pandas as pd
df = pd.read_csv("ml/data/raw/station_data_dataverse.csv")
print("Colonnes disponibles :")
print(list(df.columns))
print()
print("Aperçu :")
print(df.head(2).to_string())