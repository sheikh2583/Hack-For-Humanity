import pandas as pd
from scipy.spatial import cKDTree
import geopandas as gpd
import numpy as np

kilns = gpd.read_parquet(r'data/processed/kilns_prioritised.parquet')
labels = pd.read_excel(r'X:\AIUB Hackathon\data\processed\manual labelling\tp150.xlsx')[['lat','lon','label','kiln_class']]

tree = cKDTree(kilns[['lat','lon']].values)
dists, idxs = tree.query(labels[['lat','lon']].values, k=1)
matched = dists < 0.001

matched_labels = labels[matched]
tp = (matched_labels['label'] == 'TP').sum()
total = matched.sum()
print(matched_labels['label'].value_counts())
print('Precision:', tp, '/', total, '=', round(tp/total*100, 1), '%')
