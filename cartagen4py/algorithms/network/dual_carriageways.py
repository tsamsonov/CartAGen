import shapely
import geopandas as gpd

from cartagen4py.utils.geometry import *
from cartagen4py.utils.network import *

def collapse_dual_carriageways(roads, carriageways):
    """
    Collapse dual carriageways using the polygon skeleton made from a Delaunay Triangulation
    """

    # Retrieve crs for output
    crs = roads.crs

    # Convert geodataframe to list of dicts
    roads = roads.to_dict('records')
    carriageways = carriageways.to_dict('records')

    # Create a list of all the roads geometry of the network
    network = []
    for n in roads:
        network.append(n['geometry'])

    # Calculate the spatial index on roads
    tree = shapely.STRtree(network)

    # This list will store the indexes of roads to throw away
    originals = []
    # This will store the new collapsed geometries
    collapsed = []

    # Stores carriageways that touches either on their long side or short side
    longside = []
    shortside, shortside_list = [], []
    # Stores carriageways that touches on a single point
    pointside, pointside_list = [], []

    # Here, find touching dual carriageways
    # Loop through all carriageways polygons
    for pindex1, p1 in enumerate(carriageways):
        geom1 = p1['geometry']
        # Retrieve first boundary
        b1 = geom1.boundary
        # Loop though all carriageways polygons
        for pindex2, p2 in enumerate(carriageways):
            geom2 = p2['geometry']
            # Check if it's not the same polygon
            if geom1 != geom2:
                # If both boundaries overlap
                b2 = geom2.boundary
                if b1.overlaps(b2):
                    # Calculate intersection between the two boundaries
                    i = shapely.intersection(b1, b2)
                    # Keep only lines forming the intersection
                    if i.geom_type == 'MultiLineString':
                        line = shapely.ops.linemerge(i.geoms)
                    elif i.geom_type == 'LineString':
                        line = i
                    else:
                        # If it's not a line, continue the loop
                        continue

                    # Here, the two polygons share an edge
                    # Calculate the polygon properties
                    face = NetworkFace(geom1)
                    # Find whether the length or the width is closer to the length of the shared edge
                    if abs(line.length - face.length) < abs(line.length - face.width):
                        # Here the shared edge is the long side
                        if pindex1 not in longside:
                            longside.append(pindex1)
                        if pindex2 not in longside:
                            longside.append(pindex2)
                    else:
                        # Here, the shared edge is the short side
                        add = True
                        for shorts in shortside:
                            if shapely.equals(shorts[2], line):
                                add = False
                        if add:
                            shortside.append([pindex1, pindex2, line])
                            if pindex1 not in shortside_list:
                                shortside_list.append(pindex1)
                            if pindex2 not in shortside_list:
                                shortside_list.append(pindex2)

                # Here, stores carriageways that touches at a single point
                elif b1.crosses(b2):
                    pointside.append([pindex1, pindex2])
                    if pindex1 not in pointside_list:
                        pointside_list.append(pindex1)
                    if pindex2 not in pointside_list:
                        pointside_list.append(pindex2)

    # This will store future skeletons
    skeletons = []

    for cid, carriageway in enumerate(carriageways):
        # Get the geometry of the face
        polygon = carriageway['geometry']

        # Calculate the crossroad object
        crossroad = Crossroad(network, tree, polygon)

        # If there are more than one external road to the crossroad
        if len(crossroad.externals) > 1 and cid not in longside:
            # Retrieve the id of the external roads that have not been changed by the conversion to a crossroad object
            unchanged = crossroad.get_unchanged_roads('externals')

            # Retrieve incoming roads, i.e. the external network of the crossroad
            incoming = []
            # Looping through external roads
            for ext in crossroad.externals:
                original = None
                # Retrieve the geometry of the line
                egeom = crossroad.network[ext]
                # Looping through unchanged network
                for u in unchanged:
                    # Retrieve geometry
                    ugeom = network[u]
                    # If the line equals an unchanged line
                    if shapely.equals(egeom, ugeom):
                        # Set original to be the road object with its attributes
                        original = roads[u]
                # If an unchanged line match has been found, add the object to the list
                if original is not None:
                    incoming.append(original)
                # Else, create a new object without attributes
                else:
                    incoming.append({ "geometry": egeom })

            # Calculate the skeleton
            skeleton = SkeletonTIN(polygon, incoming=incoming, distance_douglas_peucker=3)

            skeletons.append(skeleton)

        else:
            skeletons.append(None)

            # # Storing the original geometries of the crossroad
            # originals.extend(crossroad.original)
            # # Storing the blended skeleton
            # collapsed.extend(skeleton.blended)

    def connect_short_sides(shortlist, skeletons):
        """
        Connect dual carriageways connected by their short sides.
        """
        # Get the bone junction between the two provided entry points
        def get_junction(points, skeleton):
            # Function that retrieve the first skeleton junction (degree > 2) starting from an entry point 
            def get_next_joint(point, bones):
                # Set the junction to None
                junction = None
                # Set the current point as the provided point
                cp = point
                # Set the current bone to None
                cb = None
                # Looping until a junction is found
                while junction is None:
                    # Set the next point to None
                    np = None
                    # Set the degree to 1
                    degree = 1

                    # Loop through all bones
                    for i, bone in enumerate(bones):
                        # Retrieve start and end point of bone
                        start, end = bone.coords[0], bone.coords[-1]
                        # Current point is the starting point
                        if start == cp:
                            # Set next point as end point, increment degree and set current bone to current index
                            np = end
                            degree += 1
                            cb = i
                        # Current point is the end point
                        elif end == cp:
                            # Set next point as start point, increment degree and set current bone to current index
                            np = start
                            degree += 1
                            cb = i

                    # If current bone is found, remove it from the list of bones
                    if cb is not None:
                        bones.pop(cb)
                    
                    # If the degree is above two, the junction has been found
                    if degree > 2:
                        # Set junction to current point to break the while loop
                        junction = cp
                    # Else, continue the while loop
                    else:
                        # Break the while loop if no more bone are present in the list
                        if len(bones) == 0:
                            break
                        else:
                            # Assign the current point as the next point
                            cp = np

                return junction

            # Retrieve point 1 and 2
            p1, p2 = points[0].coords[0], points[1].coords[0]

            # Retrieve the first skeleton junction for point 1 and 2
            j1 = get_next_joint(p1, skeleton.bones.copy())
            j2 = get_next_joint(p2, skeleton.bones.copy())

            # If that junction is the same point, return the point
            if j1 == j2:
                return j1
            # Else, return None
            else:
                return None

        # Treating short side connections between carriageways
        for shorts in shortlist:
            # Retrieve carriageways index and the shortside geometry
            cid1, cid2, shortline = shorts[0], shorts[1], shorts[2]
            if cid1 == 26 and cid2 == 27:
                # Retrieve both concerned skeletons
                skeleton1, skeleton2 = skeletons[cid1], skeletons[cid2]
                
                # Create a list containing entry points intersecting the short side
                shortentries = list(filter(lambda x: shapely.intersects(x, shortline), skeleton1.entries))

                # Retrieve the junction between both entries inside both skeletons
                j1 = get_junction(shortentries, skeleton1)
                j2 = get_junction(shortentries, skeleton2)

                if j1 is not None and j2 is not None:
                    connection = shapely.LineString([j1, j2])

                    ts_gdf = gpd.GeoDataFrame([{"geometry": connection}], crs=crs)
                    ts_gdf.to_file("cartagen4py/data/connection.geojson", driver="GeoJSON")

                # for entry in skeleton1.entries:
                #     if shapely.intersects(entry, shortline):
                #         # Loop through bones
                #         for bone in skeleton1.bones:
                #             # Retrieve start and end point of bone
                #             start, end = bone.coords[0], bone.coords[-1]
                #             # Add the start point or end point to the nextpoints list
                #             print(entry.coords[0])
                #             print(start)
                #             if start == point:
                #                 nextpoints.append(end)
                #             elif end == point:
                #                 nextpoints.append(start)
                #         print(entry)

    connect_short_sides(shortside, skeletons)
        
    shortdone, pointdone = [], []

    # # Launching a loop to treat carriageways depending on their connexions if there are any
    # for sk in skeletons:
    #     if sk is not None:
    #         cid1, skeleton1 = sk[0], sk[1]
    #         # Here the considered carriageways is connected by its short side with an other
    #         if cid1 in shortside_list:
    #             cid2 = None
    #             # Loop through other carriageways
    #             for shorts in shortside:
    #                 # If the connected carriageway is found, break the loop
    #                 if cid1 == shorts[0] and shorts[1] not in shortdone:
    #                     cid2 = shorts[1]
    #                     break
    #                 elif cid1 == shorts[1] and shorts[0] not in shortdone:
    #                     cid2 = shorts[0]
    #                     break
    #             # Add the carriageway  to the list of ones that have been treated
    #             shortdone.append(cid1)
    #             if cid2 is not None:
    #                 # Here, treating pairs of skeletons connected by their short side
    #                 skeleton2 = skeletons[cid2][1]
    #                 print('treating', cid1, '-', cid2)
    #             else:
    #                 # Here, the carriageway is connected by its shortside but it already has been connected to the other one
    #                 # It still requires treatment on its other sides to correctly blend inside the network
    #                 print('treating rest of', cid1, 'sides')

    #         elif cid1 in pointside_list:
    #             cid2 = None
    #             for points in pointside:
    #                 if cid1 == points[0] and points[1] not in pointdone:
    #                     cid2 = points[1]
    #                     break
    #                 elif cid1 == points[1] and points[0] not in pointdone:
    #                     cid2 = points[0]
    #                     break
    #             pointdone.append(cid1)
    #             if cid2 is not None:
    #                 # Here, treating pairs of skeletons connected by a single point
    #                 print('treating', cid1, '-', cid2, 'single point')
    #             else:
    #                 print('treating rest of', cid1, 'single sides')
    #         else:
    #             # Here, treating regular carriageways
    #             print('treating', cid1, 'normally')
    #             blended = skeleton1.blend()

    # result = []
    # remove = []
    # for c in collapsed:
    #     cgeom = c['geometry']
    #     add = True
    #     for o in originals:
    #         if shapely.equals(cgeom, network[o]):
    #             remove.append(o)
    #             add = False
    #     if add:
    #         result.append(c)

    # removeroad = []
    # for o in originals:
    #     if o not in remove:
    #         removeroad.append(o)

    # for rid, road in enumerate(roads):
    #     if rid not in removeroad:
    #         result.append(road)

    result = []
    for skeleton in skeletons:
        if skeleton is not None:
            for bone in skeleton.network:
                result.append( {"geometry": bone} )

    # ts = []
    # for shorts in shortside:
    #     ts.append({
    #         "i1": shorts[0],
    #         "i2": shorts[1],
    #         "geometry": shorts[2]
    #     })

    # ts_gdf = gpd.GeoDataFrame(ts, crs=crs)
    # ts_gdf.to_file("cartagen4py/data/touching_short.geojson", driver="GeoJSON")

    return gpd.GeoDataFrame(result, crs=crs)

    # nodes = []
    # for i, n in enumerate(skeleton.nodes):
    #     nodes.append({
    #         'nid': i,
    #         'geometry': shapely.Point(n)
    #         })
    # n = gpd.GeoDataFrame(nodes, crs=crs)
    # n.to_file("cartagen4py/data/nodes.geojson", driver="GeoJSON")

    # edges = []
    # for j, s in enumerate(skeleton.edges):
    #     edges.append({
    #         'eid': j,
    #         'start': s[0],
    #         'end': s[1],
    #         'geometry': shapely.LineString([skeleton.nodes[s[0]], skeleton.nodes[s[1]]])
    #         })
    # e = gpd.GeoDataFrame(edges, crs=crs)
    # e.to_file("cartagen4py/data/edges.geojson", driver="GeoJSON")

    # joints = []
    # for j in skeleton.joints:
    #     joints.append({
    #         'geometry': j
    #     })
    # j = gpd.GeoDataFrame(joints, crs=crs)
    # j.to_file("cartagen4py/data/joints.geojson", driver="GeoJSON")

    # bones = []
    # for b in skeleton.bones:
    #     bones.append({
    #         'geometry': b
    #     })
    # b = gpd.GeoDataFrame(bones, crs=crs)
    # b.to_file("cartagen4py/data/bones.geojson", driver="GeoJSON")

    # blend = []
    # for i, b in enumerate(blended):
    #     blend.append({
    #         'nid': i,
    #         'geometry': b
    #         })
    # bl = gpd.GeoDataFrame(blend, crs=crs)
    # bl.to_file("cartagen4py/data/blended.geojson", driver="GeoJSON")