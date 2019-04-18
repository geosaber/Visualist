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
 This script initializes the plugin, making it known to QGIS.
"""

__author__ = 'Quentin Rossy'
__date__ = '2019-04-15'
__copyright__ = '(C) 2019 by Quentin Rossy'


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load Visualist class from file Visualist.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .visualist_main import VisualistPlugin
    return VisualistPlugin()
