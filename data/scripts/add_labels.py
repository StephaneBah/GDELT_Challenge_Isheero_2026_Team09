import pandas as pd
import numpy as np

# Load mapping files
try:
    df_country = pd.read_csv('CAMEO.country.txt', sep='\t', dtype=str)
    country_map = dict(zip(df_country['CODE'], df_country['LABEL']))
except:
    country_map = {}

try:
    df_type = pd.read_csv('CAMEO.type.txt', sep='\t', dtype=str)
    type_map = dict(zip(df_type['CODE'], df_type['LABEL']))
except:
    type_map = {}

try:
    df_event = pd.read_csv('CAMEO.eventcodes.txt', sep='\t', dtype=str)
    event_map = dict(zip(df_event['CAMEOEVENTCODE'], df_event['EVENTDESCRIPTION']))
except:
    event_map = {}

quad_map = {
    '1': 'Verbal Cooperation',
    '2': 'Material Cooperation',
    '3': 'Verbal Conflict',
    '4': 'Material Conflict'
}

df = pd.read_csv('copy_events_benin_2025.csv', dtype=str)

# Functions to safely map
def map_col(col_name, mapping):
    if col_name in df.columns:
        return df[col_name].map(mapping)
    return None

# Add labels
if 'Actor1CountryCode' in df.columns:
    df.insert(df.columns.get_loc('Actor1CountryCode') + 1, 'Actor1CountryLabel', map_col('Actor1CountryCode', country_map))

if 'Actor1Type1Code' in df.columns:
    df.insert(df.columns.get_loc('Actor1Type1Code') + 1, 'Actor1Type1Label', map_col('Actor1Type1Code', type_map))
    
if 'Actor2CountryCode' in df.columns:
    df.insert(df.columns.get_loc('Actor2CountryCode') + 1, 'Actor2CountryLabel', map_col('Actor2CountryCode', country_map))

if 'Actor2Type1Code' in df.columns:
    df.insert(df.columns.get_loc('Actor2Type1Code') + 1, 'Actor2Type1Label', map_col('Actor2Type1Code', type_map))

if 'EventCode' in df.columns:
    df.insert(df.columns.get_loc('EventCode') + 1, 'EventLabel', map_col('EventCode', event_map))

if 'EventBaseCode' in df.columns:
    df.insert(df.columns.get_loc('EventBaseCode') + 1, 'EventBaseLabel', map_col('EventBaseCode', event_map))

if 'EventRootCode' in df.columns:
    # Sometimes event root code has leading zeros, ensure string match
    if df['EventRootCode'].notna().any():
        df['EventRootCode'] = df['EventRootCode'].astype(str).str.zfill(2)
    df.insert(df.columns.get_loc('EventRootCode') + 1, 'EventRootLabel', map_col('EventRootCode', event_map))

if 'QuadClass' in df.columns:
    df.insert(df.columns.get_loc('QuadClass') + 1, 'QuadClassLabel', map_col('QuadClass', quad_map))

df.to_csv('copy_events_benin_2025_labeled.csv', index=False)
print("File successfully processed and saved as copy_events_benin_2025_labeled.csv")
