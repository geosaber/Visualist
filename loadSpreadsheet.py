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

import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant
from qgis.utils import iface

from qgis.core import (QgsApplication,
                QgsVectorLayer,
                QgsProject,
                QgsSettings,
                QgsVectorFileWriter,
                QgsProcessingUtils
                )

from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm

from .utils import SpreadsheetLayersDialog

class LoadSpreadsheet(QgisAlgorithm):
    dest_id = None  # Save a reference to the output layer id

    def icon(self):
        iconName = 'excel.jpg'
        return QIcon(":/plugins/visualist/icons/" + iconName)

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return 'Utils'

    def __init__(self):
        super().__init__()
        self.success = False

    def initAlgorithm(self, config=None):
        pass

    def name(self):
        return 'Loadspreadsheet'

    def displayName(self):
        return self.tr('Load data from a spreadsheet')

    def postProcessAlgorithm(self, context, feedback):
        """
        PostProcessing Tasks to load the file as gpkg
        """
        if self.success:
            gpkg = QgsVectorLayer(self.gpkgPath, self.gpkgName)
            QgsProject.instance().addMapLayer(gpkg)
        return {}

    def processAlgorithm(self, parameters, context, feedback):
        dlg = SpreadsheetLayersDialog.SpreadsheetLayersDialog(iface.mainWindow())
        dlg.show()
        if dlg.exec_():
            layer = QgsVectorLayer(dlg.vrtPath(), dlg.layerName(), 'ogr')
            settings = QgsSettings()
            systemEncoding = settings.value('/UI/encoding', 'System')
            if not layer.isValid():
                feedback.pushInfo('Invalid Path {}'.format(dlg.gpkgPath()))
            else:
                QgsProject.instance().addMapLayer(layer)
            #Save the file as gpkg
            writer = QgsVectorFileWriter(dlg.gpkgPath(),
                                         systemEncoding,
                                         layer.fields(),
                                         layer.wkbType(),
                                         layer.crs())
            features = layer.getFeatures()
            for f in features:
                writer.addFeature(f)
            self.gpkgPath = dlg.gpkgPath()
            self.gpkgName = dlg.layerName()
            QgsProject.instance().removeMapLayer(layer)
            self.success = True
        dlg.deleteLater()
        return {}
