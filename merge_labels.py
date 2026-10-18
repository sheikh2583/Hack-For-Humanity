import pandas as pd
from scipy.spatial import cKDTree
import geopandas as gpd
import numpy as np

kilns = gpd.read_parquet(r'data/processed/kilns_prioritised.parquet')
labels = pd.read_excel(r'X:\AIUB Hackathon\data\processed\manual labelling\tp150.xlsx')[['lat','lon','label','kiln_class']]

tree = cKDTree(kilns[['lat','lon']].values)
dists, idxs = tree.query(labels[['lat','lon']].values, k=1)
matched = dists < 0.001

kilns['label'] = None
kilns['kiln_class'] = None
kilns['label'] = kilns['label'].astype('object')
kilns['kiln_class'] = kilns['kiln_class'].astype('object')

for i, (m, idx) in enumerate(zip(matched, idxs)):
    if m:
        kilns.at[idx, 'label'] = str(labels.iloc[i]['label'])
        kilns.at[idx, 'kiln_class'] = str(labels.iloc[i]['kiln_class'])

kilns['verified'] = kilns['label'].map({'TP':'Verified kiln','FP':'False positive'}).fillna('Unreviewed')
kilns.to_parquet(r'data/processed/kilns_prioritised.parquet', index=False)
print(kilns['verified'].value_counts())
print('Done.')
