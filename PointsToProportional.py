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

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QVariant

from qgis.core import (QgsGeometry,
                       QgsFeatureSink,
                       QgsFeatureRequest,
                       QgsFeature,
                       QgsField,
                       QgsProcessing,
                       QgsProcessingException,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterString,
                       QgsProcessingUtils,
                       QgsFields)

from .visualist_alg import VisualistAlgorithm
from .utils import renderers

class PointsToProportional(VisualistAlgorithm):
    dest_id = None  # Save a reference to the output layer id

    POLYGONS = 'POLYGONS'
    POINTS = 'POINTS'
    OUTPUT = 'OUTPUT'
    FIELD = 'FIELD'

    def __init__(self):
        super().__init__()

    def name(self):
        return 'proportionalsymbolsmap'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.POINTS,
                                                              self.tr('Points'), [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterFeatureSource(self.POLYGONS,
                                                              self.tr('Polygons'), [QgsProcessing.TypeVectorPolygon],optional=True))
        self.addParameter(QgsProcessingParameterString(self.FIELD,
                                                       self.tr('Count field name'), defaultValue='NUMPOINTS'))
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr('Proportional Symbols Map'), QgsProcessing.TypeVectorPoint))

    def postProcessAlgorithm(self, context, feedback):
        """
        PostProcessing Tasks to define the Symbology
        """
        output = QgsProcessingUtils.mapLayerFromString(self.dest_id, context)
        r = renderers.MapRender(output)
        r.prop(self.field_name, color = QColor(255,85,0))

        return {self.OUTPUT: self.dest_id}

    def processAlgorithm(self, parameters, context, feedback):
        poly_source = self.parameterAsSource(parameters, self.POLYGONS, context)

        point_source = self.parameterAsSource(parameters, self.POINTS, context)
        if point_source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.POINTS))

        field_name = self.parameterAsString(parameters, self.FIELD, context)
        self.field_name = field_name

        if poly_source is None:
            fields = QgsFields()
            fields.append(QgsField("fid", QVariant.Int, "int", 9, 0))
        else:
            fields = poly_source.fields()

        if fields.lookupField(field_name) < 0:
            fields.append(QgsField(field_name, QVariant.LongLong))
        field_index = fields.lookupField(field_name)

        (sink, self.dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context,
                                               fields, point_source.wkbType(),
                                               point_source.sourceCrs() if poly_source is None else poly_source.sourceCrs(),
                                               QgsFeatureSink.RegeneratePrimaryKey)
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        maximumValue = 0
        if poly_source is None:
            features = point_source.getFeatures()
            total = 100.0 / point_source.featureCount() if point_source.featureCount() else 0
            feedback.pushInfo('Number of points {}'.format(point_source.featureCount()))
            points = {}
            for current, point_feature in enumerate(features):
                if feedback.isCanceled():
                    break
                point = point_feature.geometry().asPoint()
                idList = []
                key = str(point.x()) + "_" + str(point.y())
                if key in points:
                    idList = points[key][1]
                idList.append(point_feature.id())
                points[key] = [point, idList]
            for i, key in enumerate(points):
                if feedback.isCanceled():
                    break
                point = points[key][0]
                output_feature = QgsFeature()
                inGeom = QgsGeometry()
                output_feature.setGeometry(inGeom.fromPointXY(point))
                output_feature.setAttributes([i, len(points[key][1])])
                sink.addFeature(output_feature, QgsFeatureSink.FastInsert)
                feedback.setProgress(int(current * total))
        else:
            features = poly_source.getFeatures()
            total = 100.0 / poly_source.featureCount() if poly_source.featureCount() else 0
            for current, polygon_feature in enumerate(features):
                if feedback.isCanceled():
                    break
                count = 0
                output_feature = QgsFeature()
                if polygon_feature.hasGeometry():
                    geom = polygon_feature.geometry()
                    engine = QgsGeometry.createGeometryEngine(geom.constGet())
                    engine.prepareGeometry()
                    count = 0
                    request = QgsFeatureRequest().setFilterRect(geom.boundingBox()).setDestinationCrs(poly_source.sourceCrs(), context.transformContext())
                    for point_feature in point_source.getFeatures(request):
                        if feedback.isCanceled():
                            break
                        if engine.contains(point_feature.geometry().constGet()):
                            count += 1
                    output_feature.setGeometry(geom.centroid())
                attrs = polygon_feature.attributes()
                score = count
                if field_index == len(attrs):
                    attrs.append(score)
                else:
                    attrs[field_index] = score
                output_feature.setAttributes(attrs)
                sink.addFeature(output_feature, QgsFeatureSink.FastInsert)
                feedback.setProgress(int(current * total))

        return {self.OUTPUT: self.dest_id}
