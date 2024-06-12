from cartagen4py.processes.AGENT.actions.generalisation_action import GeneralisationAction
from cartagen4py.algorithms.buildings.random_displacement import BuildingDisplacementRandom
from cartagen4py.algorithms.blocks.building_elimination import *
import geopandas as gpd

class RandomBlockDisplacementAction(GeneralisationAction):

    def __init__(self, constraint, agent, weight, section_symbols, min_sep):
        self.weight = weight
        self.agent = agent
        self.constraint = constraint
        self.section_symbols = section_symbols
        self.min_sep = min_sep
        self.name = "RandomDisplacement"

    def compute(self):
        """Compute the action, i.e. triggers the algorithm."""
        buffered_sections = [self.agent.sections.iloc[i]['geometry'].buffer(self.section_symbols[i]) for i in range(len(self.section_symbols))]
        roads_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries(buffered_sections))
        components = [component.feature['geometry'] for component in self.agent.components]
        buildings_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries(components))
        # create an empty rivers geodataframe because the algorithm takes one as input
        rivers = gpd.GeoDataFrame(columns=['geom'], geometry='geom')
        displacement = BuildingDisplacementRandom(self.min_sep, network_partitioning=False)
        displaced_gdf = displacement.displace(buildings_gdf, roads_gdf, rivers)
        for i in range(len(components)):
            component = self.agent.components[i]
            component.feature['geometry'] = displaced_gdf.iloc[i]['geometry']

class PromBlockEliminationAction(GeneralisationAction):
    nb_elim = 1

    def __init__(self, constraint, agent, weight, nb_elim):
        self.weight = weight
        self.agent = agent
        self.constraint = constraint
        self.nb_elim = 1
        self.name = "PrometheeElimination"

    def compute(self):
        """Compute the action, i.e. triggers the algorithm."""
        roads = [section['geometry'] for index, section in self.agent.sections.iterrows()]
        buildings = [component.feature['geometry'] for component in self.agent.components]
        corners, corner_areas = corner_buildings(buildings, roads)
        triangulation = block_triangulation(buildings,roads,30.0)
        congestion = []
        for building in buildings:
            congestion.append(building_congestion(building,triangulation,30.0))
        elimination = building_elimination_ranking_in_block(buildings, triangulation, congestion, 250.0, corners)
        
        for i in range(0,self.nb_elim):
            # check if we have to eliminate even more
            building = buildings[elimination[i][0][0]]
