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

import math, operator

from qgis.PyQt.QtCore import QVariant
from qgis.core import (QgsField,
                       QgsFeatureSink,
                       QgsFeature,
                       QgsGeometry,
                       QgsRectangle,
                       QgsWkbTypes,
                       QgsProcessing,
                       QgsProcessingException,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterDistance,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterFeatureSource,
                       QgsFields,
                       QgsProcessingUtils,
                       QgsFeatureRequest,
                       QgsSpatialIndex)

from .visualist_alg import VisualistAlgorithm
from .utils import renderers

class PointsToNNCluster(VisualistAlgorithm):
    dest_id = None  # Save a reference to the output layer id
    POINTS = 'POINTS'
    DIST = 'DIST'
    COUNT = 'COUNT'
    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()
    def name(self):
        return 'nearestneighboursmap'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.POINTS,
                                            self.tr('Points'), [QgsProcessing.TypeVectorPoint]))

        self.addParameter(QgsProcessingParameterDistance(self.DIST,
                                            self.tr('Maximum distance between points'),
                                            parentParameterName=self.POINTS,
                                            defaultValue=100))

        self.addParameter(QgsProcessingParameterNumber(self.COUNT,
                                            self.tr('Minimum size of the clusters'),
                                            defaultValue=10))

        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT,
                                            self.tr('Near Neighbours Clusters Map'), QgsProcessing.TypeVectorLine))

    def postProcessAlgorithm(self, context, feedback):
        """
        PostProcessing Tasks to define the Symbology
        """
        output = QgsProcessingUtils.mapLayerFromString(self.dest_id, context)
        r = renderers.MapRender(output)
        r.choropleth("COUNT")

        return {self.OUTPUT: self.dest_id}

    def processAlgorithm(self, parameters, context, feedback):

        point_source = self.parameterAsSource(parameters, self.POINTS, context)
        if point_source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.POINTS))

        self.layer = point_source
        self.index = QgsSpatialIndex()
        for feat in point_source.getFeatures():
            self.index.insertFeature(feat)

        self.d = self.parameterAsDouble(parameters, self.DIST, context)
        self.thresh = self.parameterAsDouble(parameters, self.COUNT, context)

        rand_dist = self.randDist(point_source)
        feedback.pushDebugInfo(self.tr('Expected mean distance between points is: {}'.format(rand_dist)))
        if self.d < rand_dist:
            feedback.pushDebugInfo(self.tr('You should consider to increase the distance between points parameter'))


        fields = QgsFields()
        fields.append(QgsField("fid", QVariant.Int, "int", 9, 0))
        fields.append(QgsField("AREA", QVariant.Int, "int", 9, 0))
        fields.append(QgsField("COUNT", QVariant.Int, "int", 9, 0))
        (self.sink, self.dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context,
                                               fields, QgsWkbTypes.Polygon,
                                               point_source.sourceCrs(),
                                               QgsFeatureSink.RegeneratePrimaryKey)
        if self.sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))


        self.groups = []
        self.nndist = {}
        self.nndistcount = {}
        feedback.setProgressText(self.tr('Detection of the near neighbors within a distance of {}'.format(self.d)))
        features = point_source.getFeatures()
        total = 100.0 / point_source.featureCount() if point_source.featureCount() else 0
        for current, feat in enumerate(features):
            if feedback.isCanceled():
                break
            points = self.getPoints(feat)
            if points is not None:
                self.nndist[feat.id()] = points
                self.nndistcount[feat.id()] = len(points)
            feedback.setProgress(int(current * total))
        feedback.setProgressText(self.tr('Calculation of clusters'))
        self.recurse(feedback)
        feedback.setProgressText(self.tr('Creation of the layer'))
        self.setClusters(feedback)

        return {self.OUTPUT: self.dest_id}

    def getPoints(self, feat):
        p = feat.geometry().asPoint()
        ext = QgsRectangle(p.x()-self.d,
                        p.y()-self.d,
                        p.x()+self.d,
                        p.y()+self.d)
        rawList = self.index.intersects(ext)
        if rawList is None:
            return None
        nlist = []
        if len(rawList) >= self.thresh:
            for featid in rawList:
                f = next(self.layer.getFeatures(QgsFeatureRequest(featid)))
                dist = feat.geometry().distance(f.geometry())
                if dist <= self.d:
                    nlist.append(f.id())
            return nlist
        else:
            return None

    def recurse(self, feedback):
        if feedback.isCanceled():
            return
        if len(self.nndistcount) <= 0:
            return
        maxid = max(iter(self.nndistcount.items()), key=operator.itemgetter(1))[0]
        listid = self.nndist[maxid]
        if len(listid) < self.thresh:
            return
        self.plist = []
        for featid in listid:
            feat = next(self.layer.getFeatures(QgsFeatureRequest(featid)))
            self.plist.append(feat.geometry().asPoint())
        for featid in listid.copy():
            if featid in self.nndistcount:
                del self.nndistcount[featid]
                del self.nndist[featid]
            for k, v in self.nndist.items():
                if featid in v:
                    self.nndistcount[k] -= 1
                    self.nndist[k].remove(featid)
        self.groups.append(self.plist)
        self.recurse(feedback)

    def setClusters(self, feedback):
        #Get the center of each groups and check if some point are in the wrong group
        centers = []
        clusters = []
        for group in self.groups:
            geom = QgsGeometry.fromMultiPointXY(group)
            centers.append(geom.centroid().asPoint())
            clusters.append([])
        for group in self.groups:
            for point in group:
                minDist = None
                for i in range(0,len(centers)):
                    dist = self.pointDist(centers[i], point)
                    if minDist is None:
                        minDist = dist
                        index = i
                    elif dist < minDist:
                        minDist = dist
                        index = i
                clusters[index].append(point)
        #Create symbology and add features
        for id, cluster in enumerate(clusters):
            geom = QgsGeometry.fromMultiPointXY(cluster)
            cHull = geom.convexHull()
            buffer = cHull.buffer(10, 3)
            feat = QgsFeature()
            feat.setAttributes([id, cHull.area(), int(len(cluster))])
            feat.setGeometry(buffer)
            self.sink.addFeature(feat, QgsFeatureSink.FastInsert)
            # feedback.pushInfo('addFeature: {} / {} points'.format(cHull, len(cluster)))

    # Euclidian Distance
    def pointDist(self, p1, p2):
        return math.sqrt(math.pow(p1.x()-p2.x(), 2)+math.pow(p1.y()-p2.y(), 2))

    def randDist(self, source):
        ext = source.sourceExtent()
        A = ext.height()*ext.width()
        n = source.featureCount()
        return int(round(0.5*math.sqrt(A/n)))
