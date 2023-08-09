# -*- coding: utf-8 -*-

"""
/***************************************************************************
 CartAGen4QGIS
                                 A QGIS plugin
 Cartographic generalization
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2023-05-11
        copyright            : (C) 2023 by Guillaume Touya, Justin Berli
        email                : guillaume.touya@ign.fr
 ***************************************************************************/
"""

__author__ = 'Guillaume Touya, Justin Berli'
__date__ = '2023-05-11'
__copyright__ = '(C) 2023 by Guillaume Touya, Justin Berli'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing, QgsFeatureSink, QgsProcessingAlgorithm,
    QgsFeature, QgsGeometry, QgsProcessingParameterDefinition
)
from qgis.core import (
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterDistance,
    QgsProcessingParameterMultipleLayers
)

import geopandas
from cartagen4qgis import PLUGIN_ICON
from cartagen4py import BuildingDisplacementRandom
from shapely import Polygon
from shapely.wkt import loads

class BuildingDisplacementRandomQGIS(QgsProcessingAlgorithm):
    """
    Iteratively and randomly displace buildings to avoid spatial conflicts
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT = 'OUTPUT'
    
    INPUT_BUILDINGS = 'INPUT_BUILDINGS'
    INPUT_ROADS = 'INPUT_ROADS'
    INPUT_RIVERS = 'INPUT_RIVERS'

    INPUT_NETWORK = 'INPUT_NETWORK'

    MAX_TRIALS = 'MAX_TRIALS'
    MAX_DISPLACEMENT = 'MAX_DISPLACEMENT'
    NETWORK_PARTITIONING = 'NETWORK_PARTITIONING'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_BUILDINGS,
                self.tr('Input buildings'),
                [QgsProcessing.TypeVectorPolygon]
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_ROADS,
                self.tr('Input roads'),
                [QgsProcessing.TypeVectorLine]
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_RIVERS,
                self.tr('Input rivers'),
                [QgsProcessing.TypeVectorLine]
            )
        )

        self.addParameter(
            QgsProcessingParameterDistance(
                self.MAX_DISPLACEMENT,
                self.tr('Maximum displacement allowed'),
                defaultValue=10.0,
                optional=False,
                parentParameterName='INPUT_BUILDINGS'
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.NETWORK_PARTITIONING,
                self.tr('Network partitioning'),
                defaultValue=True,
                optional=False
            )
        )
        
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.INPUT_NETWORK,
                self.tr('Input lines for the network partition'),
                layerType=QgsProcessing.TypeVectorLine,
                optional=True
            )
        )

        maxtrials = QgsProcessingParameterNumber(
            self.MAX_TRIALS,
            self.tr('Maximum number of trials'),
            type=QgsProcessingParameterNumber.Integer,
            defaultValue=25,
            optional=False
        )
        maxtrials.setFlags(maxtrials.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(maxtrials)

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Displaced')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsSource(parameters, self.INPUT_BUILDINGS, context)
        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT,
                context, source.fields(), source.wkbType(), source.sourceCrs())

        # Compute the number of steps to display within the progress bar and
        # get features from source
        total = 100.0 / source.featureCount() if source.featureCount() else 0
        features = source.getFeatures()

        roads_source = self.parameterAsSource(parameters, self.INPUT_ROADS, context)
        rivers_source = self.parameterAsSource(parameters, self.INPUT_RIVERS, context)

        maxtrials = self.parameterAsInt(parameters, self.MAX_TRIALS, context)
        maxdisp = self.parameterAsDouble(parameters, self.MAX_DISPLACEMENT, context)
        networkpart = self.parameterAsBoolean(parameters, self.NETWORK_PARTITIONING, context)

        network = self.parameterAsLayerList(parameters, self.INPUT_NETWORK, context)

        d = BuildingDisplacementRandom(
            max_trials=maxtrials,
            max_displacement=maxdisp,
            network_partitioning=networkpart
        )

        buildings = []
        attributes = []
        for f in features:
            attributes.append(f.attributes())
            wkt = f.geometry().asWkt()
            shapely_geom = loads(wkt)
            buildings.append(shapely_geom)

        buildings_geo = geopandas.GeoDataFrame(geometry=geopandas.GeoSeries(buildings))

        roads = []
        for r in roads_source.getFeatures():
            wkt = r.geometry().asWkt()
            shapely_geom = loads(wkt)
            roads.append(shapely_geom)

        roads_geo = geopandas.GeoDataFrame(geometry=geopandas.GeoSeries(roads))

        rivers = []
        for r in rivers_source.getFeatures():
            wkt = r.geometry().asWkt()
            shapely_geom = loads(wkt)
            rivers.append(shapely_geom)

        rivers_geo = geopandas.GeoDataFrame(geometry=geopandas.GeoSeries(rivers))

        simplified = None
        if networkpart:
            network_list = []
            for layer in network:
                shapes = []
                for n in layer.getFeatures():
                    wkt = n.geometry().asWkt()
                    shapely_geom = loads(wkt)
                    shapes.append(shapely_geom)
                layer_geo = geopandas.GeoDataFrame(geometry=geopandas.GeoSeries(shapes))
                network_list.append(layer_geo)
            simplified = d.displace(buildings_geo, roads_geo, rivers_geo, *network_list)
        else:
            simplified = d.displace(buildings_geo, roads_geo, rivers_geo)

        for i, simple in simplified.iterrows():
            result = QgsFeature()
            result.setGeometry(QgsGeometry.fromWkt(Polygon(simple.geometry).wkt))
            result.setAttributes(attributes[i])

            # Add a feature in the sink
            sink.addFeature(result, QgsFeatureSink.FastInsert)

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        return {
            self.OUTPUT: dest_id
        }

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Random displacement'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Buildings'

    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        return PLUGIN_ICON

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return BuildingDisplacementRandomQGIS()
