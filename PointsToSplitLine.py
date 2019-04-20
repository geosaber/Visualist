# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Visualist
                                 A QGIS plugin
 Plugin for Crime Analysts
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-04-15
        copyright            : (C) 2019 by Quentin Rossy
        email                : quentin.rossy@unil.ch
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Quentin Rossy'
__date__ = '2019-04-15'
__copyright__ = '(C) 2019 by Quentin Rossy'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSource
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingUtils
from qgis.core import QgsProcessingParameterDistance
from qgis.core import QgsProcessingParameterField

from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm
from tempfile import gettempdir

import processing, os

def count_iterable(i):
    return sum(1 for e in i)

class PointsToSplitLine(QgisAlgorithm):

    def icon(self):
        iconName = 'graduated.png'
        return QIcon(":/plugins/visualist/icons/" + iconName)

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return 'Cartography'

    def __init__(self):
        super().__init__()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource('linelayer', self.tr('Line Layer'), types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterDistance('segmentsize', self.tr('Size of the segments'), parentParameterName='linelayer', defaultValue=200))
        self.addParameter(QgsProcessingParameterField('LINES_ROAD_NAMES',
                                                    self.tr('Names of roads in line layer'),
                                                    type=QgsProcessingParameterField.String,
                                                    parentLayerParameterName='linelayer',
                                                    allowMultiple=False, defaultValue=None, optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource('pointlayer', self.tr('Point Layer'), types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterDistance('distancetoline', self.tr('Maximum Distance to the line'), parentParameterName='pointlayer', defaultValue=100))
        self.addParameter(QgsProcessingParameterField('POINTS_ROAD_NAMES',
                                    self.tr('Names of roads in point layer'),
                                    type=QgsProcessingParameterField.String,
                                    parentLayerParameterName='pointlayer',
                                    allowMultiple=False, defaultValue=None, optional=True))
        self.addParameter(QgsProcessingParameterFeatureSink('LineMap', self.tr('Graduated Segmented Line Map'), type=QgsProcessing.TypeVectorLine, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('propMap',
                                                    self.tr('Points linked to Line Map'), QgsProcessing.TypeVectorPoint))

    def name(self):
        return 'pointstosplitline'

    def displayName(self):
        return self.tr('Graduated Segmented Lines Map')

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(2, model_feedback)
        results = {}
        outputs = {}

        # v.split
        temporary_path = os.path.join(gettempdir(), 'segmented_layer.gpkg')
        try:    #valid since 3.6
            # Division des lignes par longueur maximale
            alg_params = {
                'INPUT': parameters['linelayer'],
                'LENGTH': parameters['segmentsize'],
                'OUTPUT': temporary_path
            }
            output = processing.run('native:splitlinesbylength', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            outputs['segmentedLayer'] = output['OUTPUT']
        except: #valid for 3.4-ltr + Grass
            # Division des lignes par longueur maximale
            alg_params = {
                'INPUT': parameters['linelayer'],
                'DISTANCE': parameters['segmentsize'],
                'OUTPUT': temporary_path
            }
            output = processing.run('native:segmentizebymaxdistance', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            outputs['segmentedLayer'] = output['OUTPUT']

            #Version with Grass
            # alg_params = {
            #     '-f': False,
            #     '-n': False,
            #     'GRASS_MIN_AREA_PARAMETER': 0.0001,
            #     'GRASS_OUTPUT_TYPE_PARAMETER': 2,
            #     'GRASS_REGION_PARAMETER': None,
            #     'GRASS_SNAP_TOLERANCE_PARAMETER': -1,
            #     'GRASS_VECTOR_DSCO': '',
            #     'GRASS_VECTOR_EXPORT_NOCAT': False,
            #     'GRASS_VECTOR_LCO': '',
            #     'input': parameters['linelayer'],
            #     'length': parameters['segmentsize'],
            #     'units': 1,
            #     'vertices': None,
            #     'output': temporary_path
            # }
            #
            # output = processing.run('grass7:v.split', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            # segmented_layer = QgsProcessingUtils.mapLayerFromString(output['output'], context=context)
            # outputs['segmentedLayer'] = segmented_layer


        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Graduated Lines Map
        alg_params = {
            'DIST': parameters['distancetoline'],
            'FIELD': 'NUMPOINTS',
            'LINES': outputs['segmentedLayer'],
            'STRING_MATCHING' : True,
            'LINES_ROAD_NAMES': parameters['LINES_ROAD_NAMES'],
            'POINTS': parameters['pointlayer'],
            'POINTS_ROAD_NAMES': parameters['POINTS_ROAD_NAMES'],
            'OUTPUT_LINE': parameters['LineMap'],
            'OUTPUT_POINT': parameters['propMap']
        }
        outputs['GraduatedLinesMap'] = processing.run('visualist:pointstoline', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['LineMap'] = outputs['GraduatedLinesMap']['OUTPUT_LINE']
        return results
