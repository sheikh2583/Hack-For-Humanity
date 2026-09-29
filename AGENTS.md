# KilnWatch BD: agent rules
Goal: detect brick kilns in Sentinel-2 imagery of Bangladesh, check them against siting/technology rules in config/rules.yaml, rank by exposure, show on a map.
Stack: Python 3.11, PyTorch, ultralytics (YOLO OBB), geopandas, shapely, pyproj, osmnx, earthengine-api, streamlit, folium, pytest.

Rules:
1. Never invent dataset schemas, file formats, legal thresholds or coordinates. If unknown, stop and ask me.
2. All legal numbers live in config/rules.yaml. Code reads them; never hardcode.
3. Store geometry in EPSG:4326. Do distance/area math in EPSG:9680 (WGS 84 / TM 90 NE). At startup assert pyproj can build it; otherwise fall back to EPSG:32645 (centroid lon < 90E) or EPSG:32646.
4. Every module: type hints, docstring stating input/output schema, and one pytest using tiny synthetic data.
5. Pipeline outputs are GeoParquet in data/processed/.
6. Training runs on Colab/Kaggle GPU: write notebooks/scripts, do not try to run training.
7. After each task, list what you could not verify and what I must check by hand.
