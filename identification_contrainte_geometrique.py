import geopandas as gpd
import sqlite3
from shapely.geometry import Point, LineString, Polygon

# Path vers le GeoPackage
GPKG_PATH = "Chemin/vers/le/fichier/IUGA_plan_complet.gpkg"
# ERRORS_GPKG = "errors_report.gpkg"

# Charger toutes les couches 
layers = {
    "vegetation": gpd.read_file(GPKG_PATH, layer="vegetation"),
    "mobilier_urbain": gpd.read_file(GPKG_PATH, layer="mobilier_urbain"),
    "infrastructure_urbain": gpd.read_file(GPKG_PATH, layer="infrastructure_urbain"),
    "acces": gpd.read_file(GPKG_PATH, layer="acces"),
    "mur_cloture": gpd.read_file(GPKG_PATH, layer="mur_cloture"),
    "voirie": gpd.read_file(GPKG_PATH, layer="voirie"),
    "passage_pieton": gpd.read_file(GPKG_PATH, layer="passage_pieton"),
    "espace_vert": gpd.read_file(GPKG_PATH, layer="espace_vert"),
    "batiment": gpd.read_file(GPKG_PATH, layer="batiment"),
    "aire_de_jeux": gpd.read_file(GPKG_PATH, layer="aire_de_jeux"),
}

# Dictionnaire vide pour stocker les couches d'erreurs détectées
error_layers = {}

### 1. Vérifiez les géométries non valides
for layer_name, gdf in layers.items():
    invalid_geometries = gdf[~gdf.is_valid]
    if not invalid_geometries.empty:
        error_layers[f"invalide_{layer_name}"] = invalid_geometries
        print(f"Géométries non valides trouvées dans {layer_name}")

### 2. Vérification des auto-intersections (polygones)**
for layer_name in ["voirie", "passage_pieton", "espace_vert", "batiment", "aire_de_jeux"]:
    gdf = layers[layer_name]
    self_intersections = gdf[gdf.geometry.apply(lambda geom: geom.is_valid and geom.intersects(geom))]
    if not self_intersections.empty:
        error_layers[f"Auto-intersections_{layer_name}"] = self_intersections
        print(f"Auto-intersections trouvées dans {layer_name}")

### 3. Vérifier les géométries en double
for layer_name, gdf in layers.items():
    duplicates = gdf[gdf.duplicated(subset=['geometry'], keep=False)]
    if not duplicates.empty:
        error_layers[f"doublons_{layer_name}"] = duplicates
        print(f"Géométries en double trouvées dans {layer_name}")

### 4. Valider les relations spatiales
## a) L'infrastructure doit croiser la voirie ou l'espace_vert
infra = layers["infrastructure_urbain"]
infra_errors = infra[~infra.geometry.intersects(layers["voirie"].geometry) & ~infra.geometry.intersects(layers["espace_vert"].geometry)]
if not infra_errors.empty:
    error_layers["infra_no_road"] = infra_errors
    print("Certaines infrastructures ne sont pas connectées à une voirie ou un espace vert")

## b) Les points d'accès doivent être rattachés aux bâtiments
access = layers["acces"]
access_errors = access[~access.geometry.intersects(layers["batiment"].geometry)]
if not access_errors.empty:
    error_layers["access_not_linked"] = access_errors
    print("Certains points daccès ne sont pas liés à un bâtiment.")

## c) Les arbres doivent être à l'intérieur des espaces verts
trees = layers["vegetation"]
tree_errors = trees[~trees.geometry.intersects(layers["espace_vert"].geometry)]
if not tree_errors.empty:
    error_layers["arbres_extérieur_vert"] = tree_errors
    print("Certains arbres ne sont pas situés dans un espace vert.")

## d) Les arbres doivent être espacés d'au moins 1 m
from shapely.ops import unary_union
tree_union = unary_union(trees.geometry)
tree_errors = trees[trees.geometry.apply(lambda tree: tree_union.distance(tree) < 1)]
if not tree_errors.empty:
    error_layers["arbres_trop_près"] = tree_errors
    print("Certains arbres sont trop proches (<1m).")

## e) Le mobilier urbain ne doit pas être placé sur les routes ou dans les bâtiments
furniture = layers["mobilier_urbain"]
furniture_errors = furniture[furniture.geometry.intersects(layers["voirie"].geometry) | furniture.geometry.intersects(layers["batiment"].geometry)]
if not furniture_errors.empty:
    error_layers["meubles_mauvais_emplacement"] = furniture_errors
    print("Certains mobiliers urbains sont placés dans une voirie ou un bâtiment")

## f) Les aires de jeux doivent être situées à l'intérieur d'espaces verts
playgrounds = layers["aire_de_jeux"]
playground_errors = playgrounds[~playgrounds.geometry.intersects(layers["espace_vert"].geometry)]
if not playground_errors.empty:
    error_layers["aire_de_jeu_sans_vert"] = playground_errors
    print("Certaines aires de jeux ne sont pas situées dans un espace vert")


# 5.Vérification des superpositions (chevauchements) de polygones de la même couche
for layer_name in ["voirie", "passage_pieton", "espace_vert", "batiment", "aire_de_jeux"]:
    gdf = layers[layer_name]
    intersections = []

    # a) Vérification des superpositions entre polygones de la même couche
    for idx_a, geom_a in gdf.iterrows():
        for idx_b, geom_b in gdf.iterrows():
            if idx_a < idx_b:  # Evite de vérifier un polygone avec lui-même
                # Vérification des superpositions
                if geom_a['geometry'].overlaps(geom_b['geometry']):
                    intersections.append((idx_a, idx_b))  # Ajoute l'indice des géométries en intersection

    # b) Si des superpositions sont trouvées, les ajouter au dictionnaire d'erreurs
    if intersections:
        error_layers[f"intersect_{layer_name}"] = intersections
        print(f"Superpositions trouvées dans {layer_name}: {intersections}")

# Affichage du nombre d'erreurs pour chaque type d'erreur après la boucle
for error_type, error_data in error_layers.items():
    print(f"{error_type}: {len(error_data)} erreurs trouvées.")

# Si aucune erreur n'est trouvée, afficher un message
if not error_layers:
    print("Aucune erreur détectée.")
    
# 6. Vérification des contours communs 
# Récupération des données géométriques pour les passages piétons et la voirie
passages = layers["passage_pieton"]
voirie = layers["voirie"]

# Liste pour stocker les index des passages piétons qui ne s'intersectent pas avec la voirie
passages_sans_intersection = []

# Parcours de chaque passage piéton
for idx, row in passages.iterrows():
    geom_passage = row.geometry
    # Vérification : le passage piéton doit être intersecté ou touché par au moins une entité de la voirie
    condition_valide = any(road.intersects(geom_passage) or road.touches(geom_passage) for road in voirie.geometry)
    if not condition_valide:
        passages_sans_intersection.append(idx)

# Enregistrement des erreurs dans le dictionnaire error_layers et affichage du nombre d'erreurs trouvées
if passages_sans_intersection:
    error_layers["passage_pieton_sans_intersection_voirie"] = passages.loc[passages_sans_intersection]
    print("Certains passages piétons ne respectent pas les contraintes de contenance et/ou de continuité avec la voirie.")
    print(f"passage_pieton_intersection_voirie: {len(passages_sans_intersection)} erreurs trouvées.")
else:
    print("passage_pieton_intersection_voirie: 0 erreurs trouvées.")