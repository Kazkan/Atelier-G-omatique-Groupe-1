from PyQt5.QtWidgets import QDialog, QVBoxLayout, QComboBox, QPushButton, QHBoxLayout, QLabel, QMessageBox
# Importe les outils de PyQt5 pour créer une boîte de dialogue avec des boutons, labels, menus déroulants, etc.

from qgis.core import *
# Importe les classes principales de QGIS (couches, géométrie, projet, etc.)

from qgis.utils import iface
# Importe l'interface de QGIS (permet d'interagir avec la carte, etc.)

import math
# Importe le module math (même si ici il n’est pas utilisé)

# Crée une classe pour la boîte de dialogue de sélection des couches
class SelectLayerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)  # Appelle le constructeur de la boîte de dialogue
        self.setWindowTitle("Select Layers")  # Titre de la fenêtre

        layout = QVBoxLayout(self)  # Crée un layout vertical (empile les éléments)

        # Crée une liste déroulante pour choisir la couche de points
        self.point_layer_combobox = QComboBox()
        # Ajoute les noms de toutes les couches de type "Point" du projet dans la liste déroulante
        self.point_layer_combobox.addItems([
            layer.name() for layer in QgsProject.instance().mapLayers().values()
            if layer.geometryType() == QgsWkbTypes.PointGeometry
        ])
        layout.addWidget(QLabel("Select Point Layer:"))  # Ajoute un label au-dessus de la liste
        layout.addWidget(self.point_layer_combobox)       # Ajoute la liste déroulante dans la fenêtre

        # Crée une liste déroulante pour choisir la couche de polygones
        self.polygon_layer_combobox = QComboBox()
        # Ajoute les noms de toutes les couches de type "Polygon" du projet dans la liste déroulante
        self.polygon_layer_combobox.addItems([
            layer.name() for layer in QgsProject.instance().mapLayers().values()
            if layer.geometryType() == QgsWkbTypes.PolygonGeometry
        ])
        layout.addWidget(QLabel("Select Polygon Layer:"))  # Ajoute un label
        layout.addWidget(self.polygon_layer_combobox)      # Ajoute la liste déroulante dans la fenêtre

        # Crée un bouton pour appliquer les sélections
        button_layout = QHBoxLayout()  # Layout horizontal pour les boutons
        self.apply_button = QPushButton("Apply")  # Crée un bouton "Apply"
        self.apply_button.clicked.connect(self.apply_selection)  # Quand on clique, on appelle une fonction
        button_layout.addWidget(self.apply_button)  # Ajoute le bouton au layout

        layout.addLayout(button_layout)  # Ajoute le layout des boutons dans la boîte de dialogue

    def apply_selection(self):
        # Récupère le nom de la couche de points sélectionnée
        point_layer_name = self.point_layer_combobox.currentText()
        # Récupère le nom de la couche de polygones sélectionnée
        polygon_layer_name = self.polygon_layer_combobox.currentText()

        self.accept()  # Ferme la boîte de dialogue
        self.process_layers(point_layer_name, polygon_layer_name)  # Lance le traitement

    def process_layers(self, point_layer_name, polygon_layer_name):
        # Récupère la couche de points à partir de son nom
        point_layer = QgsProject.instance().mapLayersByName(point_layer_name)[0]
        # Récupère la couche de polygones à partir de son nom
        polygon_layer = QgsProject.instance().mapLayersByName(polygon_layer_name)[0]

        problematic_points = []  # Liste des points à problème

        # Vérifie les points qui ne sont dans aucun polygone
        points_not_inside = self.check_points_not_in_polygon(point_layer, polygon_layer)

        # Vérifie les points trop proches (< 1 mètre)
        points_too_close = self.check_points_too_close(point_layer)

        # Combine les deux listes de points problématiques (sans doublons)
        problematic_points = list(set(points_not_inside + points_too_close))

        # Affiche un message avec le nombre de points problématiques
        QMessageBox.information(self, "Problematic Points", f"Found {len(problematic_points)} problematic points.")

        # Sélectionne les points problématiques dans QGIS
        point_layer.selectByIds(problematic_points)

    def check_points_not_in_polygon(self, point_layer, polygon_layer):
        problematic_points = []  # Liste pour les points en dehors des polygones

        for point_feature in point_layer.getFeatures():  # Parcourt chaque point
            point = point_feature.geometry().centroid().asPoint()  # Récupère la position du point
            found_polygon = False  # Indique si le point est dans un polygone

            for polygon_feature in polygon_layer.getFeatures():  # Parcourt les polygones
                if polygon_feature.geometry().contains(point):  # Si le polygone contient le point
                    found_polygon = True
                    break  # Pas besoin de chercher plus

            if not found_polygon:  # Si aucun polygone ne contient ce point
                problematic_points.append(point_feature.id())  # On ajoute son ID à la liste

        return problematic_points  # Retourne la liste des points hors polygones

    def check_points_too_close(self, point_layer):
        problematic_points = []  # Liste pour les points trop proches
        tolerance = 1.0  # Distance minimale (1 mètre)
        points = []  # Liste des positions des points

        for point_feature in point_layer.getFeatures():  # Parcourt tous les points
            points.append(point_feature.geometry().centroid().asPoint())  # Stocke les positions

        # Compare chaque paire de points
        for i, point1 in enumerate(points):
            for j, point2 in enumerate(points):
                if i != j and point1.distance(point2) < tolerance:  # Si distance < 1m
                    problematic_points.append(i)  # Ajoute l’index du point

        return list(set(problematic_points))  # Retourne la liste sans doublons


# Fonction principale qui ouvre la boîte de dialogue
def main():
    dialog = SelectLayerDialog()  # Crée une instance de la boîte de dialogue
    dialog.exec_()  # Affiche la boîte de dialogue

# Lance le script
main()
