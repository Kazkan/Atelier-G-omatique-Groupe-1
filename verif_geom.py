from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
import processing

class Modle(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('polygone1', 'polygone1', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Polygone_non_valide', 'polygone_non_valide', optional=True, type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Polygone_valide', 'polygone_valide', optional=True, type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(1, model_feedback)
        results = {}
        outputs = {}

        # Vérifier la validité
        alg_params = {
            'IGNORE_RING_SELF_INTERSECTION': False,
            'INPUT_LAYER': parameters['polygone1'],
            'METHOD': 2,  # GEOS
            'INVALID_OUTPUT': parameters['Polygone_non_valide'],
            'VALID_OUTPUT': parameters['Polygone_valide']
        }
        outputs['VrifierLaValidit'] = processing.run('qgis:checkvalidity', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Polygone_non_valide'] = outputs['VrifierLaValidit']['INVALID_OUTPUT']
        results['Polygone_valide'] = outputs['VrifierLaValidit']['VALID_OUTPUT']
        
        # Compter le nombre de polygones non valides
        layer = context.getMapLayer(results['Polygone_non_valide'])
        if layer:
            error_count = layer.featureCount()
            print(f"Nombre de polygones avec erreur : {error_count}")
        else:
            print("Impossible de déterminer le nombre de polygones erronés.")

        return results

    def name(self):
        return 'Modèle'

    def displayName(self):
        return 'Modèle'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return Modle()
