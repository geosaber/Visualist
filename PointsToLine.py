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

import math, os
import urllib.parse
from tempfile import gettempdir

from shapely.geometry import LineString, MultiPoint
from shapely.ops import split

from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtCore import QVariant
from qgis.utils import iface
from qgis.core import (QgsApplication,
                       QgsField,
                       QgsFeatureSink,
                       QgsFeature,
                       QgsGeometry,
                       QgsLineString,
                       QgsPoint,
                       QgsPointXY,
                       QgsRectangle,
                       QgsWkbTypes,
                       QgsProcessing,
                       QgsProcessingException,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterExtent,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterDistance,
                       QgsProcessingParameterCrs,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterString,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterField,
                       QgsProcessingParameterVectorLayer,
                       QgsFields,
                       QgsProcessingUtils,
                       QgsFeatureRequest,
                       QgsSpatialIndex,
                       QgsCoordinateTransform,
                       QgsVectorLayer,
                       QgsProject,
                       QgsStringUtils,
                       QgsMessageLog)

from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm
import processing

from .utils import renderers

# SK: Librairies pour comparaison chaine de caracteres des rues
import csv, re, unicodedata

#Convenient function to debug
NAME = "Visualist"
log = lambda m: QgsMessageLog.logMessage(m, NAME)

def count_iterable(i):
    return sum(1 for e in i)


class PointsToLine(QgisAlgorithm):
    LINES = 'LINES'
    POINTS = 'POINTS'
    DIST = 'DIST'
    FIELD = 'FIELD'
    POINTS_ROAD_NAMES = 'POINTS_ROAD_NAMES'
    LINES_ROAD_NAMES = 'LINES_ROAD_NAMES'
    OUTPUT_POINT = 'OUTPUT_POINT'
    OUTPUT_LINE = 'OUTPUT_LINE'

    def icon(self):
        iconName = 'graduated.png'
        return QIcon(":/plugins/visualist/icons/" + iconName)

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return 'Cartography'

    def __init__(self):
        super().__init__()

    def helpUrl(self):
        url = os.path.join("file:///"+os.path.dirname(__file__).replace("\\","/"),"help/build/html/index.html")
        log(url)
        return url

    def shortDescription(self):
        help = """Graduated line maps represent the number of events along roads (polyline layer).
            Events are projected onto the segments closest to their positions,
            but only if the distance between them is less than a configurable threshold (e. g. 50 meters)."""
        return help

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.LINES,
                                            self.tr('Line Layer'),
                                            types=[QgsProcessing.TypeVectorLine],
                                            defaultValue=None))


        self.addParameter(QgsProcessingParameterField(self.LINES_ROAD_NAMES,
                                            self.tr('Names of roads in line layer'),
                                            type=QgsProcessingParameterField.String,
                                            parentLayerParameterName=self.LINES,
                                            allowMultiple=False, defaultValue=None, optional=True))

        self.addParameter(QgsProcessingParameterFeatureSource(self.POINTS,
                                            self.tr('Point Layer'),
                                            types=[QgsProcessing.TypeVectorPoint],
                                            defaultValue=None))

        self.addParameter(QgsProcessingParameterDistance(self.DIST,
                                                    self.tr('Maximum distance to the line'),
                                                    parentParameterName=self.POINTS,
                                                    defaultValue=100))


        self.addParameter(QgsProcessingParameterField(self.POINTS_ROAD_NAMES,
                                    self.tr('Names of roads in point layer'),
                                    type=QgsProcessingParameterField.String,
                                    parentLayerParameterName=self.POINTS,
                                    allowMultiple=False, defaultValue=None, optional=True))

        self.addParameter(QgsProcessingParameterString(self.FIELD,
                                                    self.tr('Count field name'), defaultValue='NUMPOINTS'))
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT_LINE,
                                                    self.tr('Graduated Line Map'), QgsProcessing.TypeVectorLine))
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT_POINT,
                                                    self.tr('Points linked to Line Map'), QgsProcessing.TypeVectorPoint))
    def name(self):
        return 'pointstoline'

    def displayName(self):
        return self.tr('Graduated Lines Map')


    def postProcessAlgorithm(self, context, feedback):
        """
        PostProcessing Tasks to define the Symbology
        """
        output = QgsProcessingUtils.mapLayerFromString(self.dest_id, context)
        r = renderers.MapRender(output)
        r.prop(self.field_name, type=renderers.LINE)

        output = QgsProcessingUtils.mapLayerFromString(self.dest_id_point, context)
        r = renderers.MapRender(output)
        r.prop(self.field_name, color = QColor(255,85,0))
        path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "utils/styles/asLine.qml")
        feedback.pushInfo('Load symbology from file: {})'.format(path))
        output.loadNamedStyle(path)
        output.triggerRepaint()
        return {self.OUTPUT_LINE: self.dest_id}

    # SK: Pre-traitement pour distance de Levenshtein
    def NameClean(self, address, feedback):
        noise = re.compile("(?<![a-z])rue|av\.|avenue|(?<![a-z])bd(?![a-z])|boulevard|ch\.|chemin|(?<![a-z])rte|route|^q\.|quai|quartier|passage|(?<![a-z])voie|(?<![a-z])allee|rlle|(?<![a-z])[dl][aeu]s*(?![a-z])|bis|[0-9]+[a-z]|[0-9]+|d\'|l\'|(?<![a-z])[a-z]{1}(?![a-z])|cff")
        n = ' '.join(str(address).split("/",2)[0].split())
        n = ' '.join(n.split())
        n = n.lower().replace('-',' ').replace('pl.','place').replace(',',' ').replace('"',' ')
    #    n = unicodedata.normalize("NFD", unicode(n,"Utf-8")).encode("ascii", "ignore")
        if type(n) is str: # test erreur certaines lignes non unicode depuis QGIS
            n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore") #'ignore' : supprime le caractere s'il y a une erreur
        else:
            n = unicodedata.normalize("NFKD", str(n,"Utf-8")).encode("ascii", "ignore") #pour les chaines vides
            # fix_print_with_import
            feedback.pushInfo('Non-unicode line: {}'.format(address))
        n = re.sub(noise, '', n.decode('ascii'), count=0, flags=0)
        n = ' '.join(sorted(n.split(), key=str.lower))
        return n

    def processAlgorithm(self, parameters, context, feedback):
        line_source = self.parameterAsSource(parameters, self.LINES, context)
        if line_source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.LINES))

        point_source = self.parameterAsSource(parameters, self.POINTS, context)
        if point_source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.POINTS))

        distance = self.parameterAsDouble(parameters, self.DIST, context)
        field_rn_line = self.parameterAsString(parameters, self.LINES_ROAD_NAMES, context)
        field_rn_point = self.parameterAsString(parameters, self.POINTS_ROAD_NAMES, context)
        if field_rn_line:
            feedback.pushInfo('Calculation with Levenshtein matching between \'{}\' (lines) and \'{}\' (points)'.format(field_rn_line, field_rn_point))
            field_rn_line_index = line_source.fields().lookupField(field_rn_line)
            if field_rn_point is None:
                raise QgsProcessingException(self.invalidSourceError(parameters, self.POINTS_ROAD_NAMES))
        if field_rn_point:
            field_rn_point_index = point_source.fields().lookupField(field_rn_point)
            # raise QgsProcessingException(self.invalidSourceError(parameters, self.POINTS_ROAD_NAMES))

        field_name = self.parameterAsString(parameters, self.FIELD, context)
        self.field_name = field_name

        fields = line_source.fields()
        fields.append(QgsField(field_name, QVariant.LongLong))
        field_count_index = fields.lookupField(field_name)
        if fields.lookupField('fid') < 0:
            fields.append(QgsField('fid', QVariant.Int))
        field_id_index = fields.lookupField('fid')

        fields_point = QgsFields()
        fields_point.append(QgsField("fid", QVariant.Int, "int", 9, 0))
        fields_point.append(QgsField("line_id", QVariant.Int, "int", 9, 0))
        fields_point.append(QgsField(self.field_name, QVariant.LongLong))
        field_point_count_index = fields_point.lookupField(field_name)
        field_point_id_index = fields_point.lookupField('fid')
        field_point_lid_index = fields_point.lookupField('line_id')
        if field_rn_point:
            fields_point.append(QgsField(field_rn_point, QVariant.String))
            field_point_rname_index = fields_point.lookupField(field_rn_point)
            fields_point.append(QgsField(field_rn_point+"_levenshtein", QVariant.String))
            field_point_rname_clean_index = fields_point.lookupField(field_rn_point+"_levenshtein")

        (self.sink, self.dest_id) = self.parameterAsSink(parameters, self.OUTPUT_LINE, context,
                                               fields, line_source.wkbType(), line_source.sourceCrs(), QgsFeatureSink.RegeneratePrimaryKey)
        if self.sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT_LINE))

        (self.sink_point, self.dest_id_point) = self.parameterAsSink(parameters, self.OUTPUT_POINT, context,
                                               fields_point, point_source.wkbType(), point_source.sourceCrs(), QgsFeatureSink.RegeneratePrimaryKey)
        if self.sink_point is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT_POINT))

        # context.addLayerToLoadOnCompletion( self.OUTPUT_POINT,
        #             QgsProcessingContext.LayerDetails(name = self.OUTPUT_POINT, project=context.project() ))

        #Calculate Proportional Symbol Map
        features = point_source.getFeatures()
        total = 100.0 / point_source.featureCount() if point_source.featureCount() else 0
        feedback.setProgressText(self.tr('Create a Proportional Symbols Map with points'))
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
            if field_rn_point:
                points[key].append(point_feature[field_rn_point_index])
        for i, key in enumerate(points):
            if feedback.isCanceled():
                break
            point = points[key][0]
            output_feature = QgsFeature()
            inGeom = QgsGeometry()
            output_feature.setGeometry(inGeom.fromPointXY(point))
            attrs = [i, None, len(points[key][1])]
            if field_rn_point:
                attrs.append(points[key][2])
                attrs.append(self.NameClean(points[key][2], feedback))
            output_feature.setAttributes(attrs)
            self.sink_point.addFeature(output_feature, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(current * total))


        #Calculate Graduated Line Map
        prop_point_source = QgsProcessingUtils.mapLayerFromString(self.dest_id_point, context)
        prop_point_source.startEditing()
        segList = {}
        t = QgsCoordinateTransform(point_source.sourceCrs(), line_source.sourceCrs(), context.transformContext())
        request = QgsFeatureRequest().setFilterRect(t.transform(line_source.sourceExtent(), QgsCoordinateTransform.ReverseTransform))
        count = count_iterable(prop_point_source.getFeatures(request))
        total = 100.0 / count if count else 0
        feedback.setProgressText(self.tr('Calculate the number points for each segment'))
        for current, point_feature in enumerate(prop_point_source.getFeatures(request)):
            if feedback.isCanceled():
                break
            minDist = None
            minFeatId = None
            point = point_feature.geometry().asPoint()
            point = t.transform(point)
            pointBox = QgsRectangle(
                point.x()-distance,
                point.y()-distance,
                point.x()+distance,
                point.y()+distance
            )
            request = QgsFeatureRequest().setFilterRect(pointBox)

            if field_rn_line:
                # récupérer le nom de la rue pour feat
                pointRoadName = point_feature[field_point_rname_index]
                #Première boucle pour identifier la rue qui match le mieux
                bestMatchingFeats = None
                matchingScores = {}
                bestMatchingScore = None
                #SK : pre-traitement du point
                pointRoadNameClean = self.NameClean(pointRoadName, feedback)
                if pointRoadNameClean != '': # verifie qu'il y a bien un nom de rue pour le point
                    minDist = None
                    for line_feature in line_source.getFeatures(request):
                        # feedback.pushInfo('Line: {}'.format(line_feature))
                        if feedback.isCanceled():
                            break
                        # récupérer le nom de la rue pour inFeat
                        lineRoadName = line_feature[field_rn_line_index]
                        # SK: pre-traitement segment
                        lineRoadNameClean = self.NameClean(lineRoadName, feedback)
                        if pointRoadNameClean == '': # verifie qu'il y a bien un nom de rue pour la ligne
                            continue
                        # SK: Calcul de la distance de Levenshtein
                        matchScore = QgsStringUtils.levenshteinDistance(pointRoadNameClean,lineRoadNameClean)
                        if matchScore is not None:
                            #on stock tous les scores dans un dictionnaire que l'on interrogera plus tard avec le meilleur score
                            #on stock la liste des feature pour chaque score
                            if matchScore in matchingScores:
                                matchingScores[matchScore].append(line_feature)
                            else:
                                matchingScores[matchScore] = [line_feature]
                            #On identifie le meilleur score dans la boucle
                            if bestMatchingScore is None or matchScore < bestMatchingScore:
                                bestMatchingScore = matchScore
                        #QR : compute minDist in case MatchingScore is empty
                        geom = line_feature.geometry()
                        dist = geom.closestSegmentWithContext(point) #closestVertex
                        if minDist == None or dist[0] < minDist:
                            minDist = dist[0]
                            minFeatId = line_feature.id()
                    #On récupère la liste des segments qui ont le meilleur matching
                    if bestMatchingScore is None: #Gestion erreur inconnue
                        if minFeatId is not None:
                            feedback.pushInfo('No matching line for {} at line: {} (closest road id used: {})'.format(pointRoadName, current, minFeatId))
                    else:
                        bestMatchingFeats = matchingScores[bestMatchingScore]
                        #réutiliser ici la liste "bestMatchingFeats" pour assurer que les 2 conditions soient prises en compte : matchingName + distance la plus courte
                        minDist = None
                        oldFeatId = minFeatId
                        minFeatId = None
                        for line_feature in bestMatchingFeats:
                            geom = line_feature.geometry()
                            dist = geom.closestSegmentWithContext(point) #closestVertex
                            if minDist == None or dist[0] < minDist:
                                minDist = dist[0]
                                minFeatId = line_feature.id()
                        # if oldFeatId != minFeatId:
                        #     feedback.pushInfo('Line change based on name {} - {} for {})'.format(oldFeatId, minFeatId, pointRoadName))

                else: # si le champ nom est vide
                    minDist = None
                    minFeatId = None
                    # passe au calcul juste sur la distance
                    for line_feature in line_source.getFeatures(request):
                        # feedback.pushInfo('Line: {}'.format(line_feature))
                        if feedback.isCanceled():
                            break
                        geom = line_feature.geometry()
                        dist = geom.closestSegmentWithContext(point) #closestVertex
                        if minDist == None or dist[0] < minDist:
                            minDist = dist[0]
                            minFeatId = line_feature.id()
                    feedback.pushInfo('Cleaned address is Empty for {} at line {} (closest road id used: {})'.format(pointRoadName, current, minFeatId))

                    #FIN
            else:
                for line_feature in line_source.getFeatures(request):
                    # feedback.pushInfo('Line: {}'.format(line_feature))
                    if feedback.isCanceled():
                        break
                    geom = line_feature.geometry()
                    dist = geom.closestSegmentWithContext(point) #closestVertex
                    if minDist == None or dist[0] < minDist:
                        minDist = dist[0]
                        minFeatId = line_feature.id()

            if minFeatId is not None:
                if minFeatId in segList:
                    segList[minFeatId]["TOT"] += point_feature[field_point_count_index]
                else:
                    segList[minFeatId] = {"TOT" : point_feature[field_point_count_index]}
                prop_point_source.changeAttributeValue(point_feature.id(), field_point_lid_index, minFeatId)
            feedback.setProgress(int(current * total))
        prop_point_source.commitChanges()
        if len(segList) == 0:
            feedback.reportError(self.tr('No match between points and lines layers'), fatalError=True)
            return {}

        feedback.setProgressText(self.tr('Create the layer'))
        total = 100.0 / len(segList)
        current = 0
        for fid, values in segList.items():
            feat = QgsFeature()
            line_source.getFeatures(QgsFeatureRequest(fid)).nextFeature(feat)
            attrs = feat.attributes()
            attrs.append(values["TOT"]) #count
            attrs.append(fid)
            output_feature = QgsFeature()
            output_feature.setGeometry(feat.geometry())
            output_feature.setAttributes(attrs)
            self.sink.addFeature(output_feature, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(current * total))
            current += 1

        return {self.OUTPUT_LINE: self.dest_id}
