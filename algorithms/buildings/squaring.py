# This is an implementation of the least squares based squaring algorithm proposed by Lokhat & Touya (https://hal.science/hal-02147792)

import numpy as np

# rank of key p in a dict
def get_rank(dict_p, p):
    for i, e in enumerate(dict_p):
        if e == p:
            return i
    return -1

# returns a list of coordinates from a shapely linestring, multilinestring or polygon 
def get_coords(shape):
    if shape.geom_type == 'MultiLineString':
        return shape[0].coords 
    elif shape.geom_type == 'Polygon':
        return shape.exterior.coords
    elif shape.geom_type == 'LineString':
        return shape.coords
    return []

class Squarer:
    """Initialize squaring object, with default weights and tolerance set in the constructor
    """
    def __init__(self, max_iter=1000, norm_tol=0.05,rtol=10, ftol=0.11, hrtol=7, pfixe=5, p90=100, p0=50, p45=10, switch_new=False):
        self.SWITCH_NEW = switch_new
        self.MAX_ITER = max_iter
        self.NORM_DIFF_TOL = norm_tol
        self.rightTol = rtol # 10 90° angles tolerance
        self.flatTol = ftol # 0.11 flat angles tolerance
        self.semiRightTol = hrtol # 7 45/135° angles tolerance
        self.poidsPtfFixe = pfixe #5
        self.poids90 = p90 #100
        self.poids0 = p0 #50
        self.poids45 = p45 #10

        self.point_shapes = {}
        self.lines_pindex = []
        self.indicesRight, self.indicesFlat, self.indicesHrAig, self.indicesHrObt = [], [], [], []

    # get a dict where the key is the tuple of a point and the associated value is 
    # the table of indices of the geometries the point belongs to
    def build_dict_of_unique_points(self, shapes):
        for i, s in enumerate(shapes):
            #coords = s[0].coords if shapes[0].geom_type == 'MultiLineString' else s.exterior.coords
            coords = get_coords(s)
            for p in coords:
                #print(p) # tuple
                if p in self.point_shapes:
                    if i not in self.point_shapes[p]:
                        self.point_shapes[p].append(i)
                else:
                    self.point_shapes[p] = [i]


    # get a list where each geometry is made of a list of the indices of the points forming the geometry.
    def build_pindex_for_shapes(self, shapes):
        for s in shapes:
            index_points = []
            #coords = s[0].coords if shapes[0].geom_type == 'MultiLineString' else s.exterior.coords
            coords = get_coords(s)
            for p in coords:
                index_points.append(get_rank(self.point_shapes, p))
            self.lines_pindex.append(index_points)

    # get the rank of the point of index idx_p in the shape of index idx_s
    def get_rank_point_in_shape(self, idx_p, idx_s):
        for i, idx_pp in enumerate(self.lines_pindex[idx_s]):
            if idx_pp == idx_p: return i
        return -1

    # get the list of potential angles around the point of index idx_p as a triplet of indices [[idx_prev, idx_p, idx_next]...]
    def get_angle_triplets(self, idx_p, unik_points):
        p = unik_points[idx_p]
        lines_containing_p = self.point_shapes[p]
        if len(lines_containing_p) == 1:
            idx_l = lines_containing_p[0]
            r = self.get_rank_point_in_shape(idx_p, idx_l)
            # single node, no angle
            if r == 0 or r == len(self.lines_pindex[idx_l]) - 1 : 
                return []
            # interior point of a line
            idx_prev = self.lines_pindex[idx_l][r - 1]
            idx_next = self.lines_pindex[idx_l][r + 1]
            #print(f'POINT({p[0]} {p[1]})')
            return [[idx_prev, idx_p, idx_next]]
        # points intersecting multiple lines
        else:
            triplets = []
            #print(f'POINT({p[0]} {p[1]})')
            for i in range(len(lines_containing_p) - 1):
                idx_l1 = lines_containing_p[i]
                r = self.get_rank_point_in_shape(idx_p, idx_l1)
                idx_prev = self.lines_pindex[idx_l1][r - 1] if r > 0 else self.lines_pindex[idx_l1][r + 1]
                for j in range(i + 1, len(lines_containing_p)):
                    idx_l2 = lines_containing_p[j]
                    r = self.get_rank_point_in_shape(idx_p, idx_l2)
                    idx_next = self.lines_pindex[idx_l2][r - 1] if r > 0 else self.lines_pindex[idx_l2][r + 1]
                    triplets.append([idx_prev, idx_p, idx_next])
            return triplets

    def get_vecs_around(self, t, unik_points) : # t = [idx_prec, idx_p, idx_suiv]
        """ return vectors formed by a triplet of indexes
        """
        pr, p, s = unik_points[t[0]], unik_points[t[1]], unik_points[t[2]]
        if self.SWITCH_NEW:
            v1 = np.array([pr[0] - p[0], pr[1] - p[1]])
        else:
            v1 = np.array([p[0] - pr[0], p[1] - pr[1]])
        v2 = np.array([s[0] - p[0], s[1] - p[1]])
        return v1, v2

    def idx_angles_remarquables(self, unik_points):
        #unik_points = list(self.point_shapes)
        rTol = np.cos((np.pi / 2) - self.rightTol * np.pi / 180)
        hrTol1 = np.cos((np.pi / 4) - self.semiRightTol * np.pi / 180)
        hrTol2 = np.cos((np.pi / 4) + self.semiRightTol * np.pi / 180)
        for idx_p in range(len(unik_points)):
            triplets = self.get_angle_triplets(idx_p, unik_points)
            for t in triplets:
                v1, v2 = self.get_vecs_around(t, unik_points)
                n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
                v1n = v1 / n1 if n1 != 0. else np.array([0.,0.]) #n1
                v2n = v2 / n2 if n2 != 0. else np.array([0.,0.]) #n2
                dot = v1n.dot(v2n)
                cross = np.cross(v1n, v2n).item(0)
                if (np.abs(dot) <= rTol):
                    self.indicesRight.append(t)
                elif (cross <= self.flatTol):
                    self.indicesFlat.append(t)
                elif (dot <= hrTol1 and dot >= hrTol2):
                    self.indicesHrAig.append(t)
                elif (dot >= -hrTol1 and dot <= -hrTol2):
                    self.indicesHrObt.append(t)
        print(f'potential angles -- R: {len(self.indicesRight)} - F: {len(self.indicesFlat)} - HRa: {len(self.indicesHrAig)} - HRo: {len(self.indicesHrObt)}')


    def get_Y(self, unik_points):
        """ Observation vector
        """
        nb_points = len(unik_points)
        self.Y = np.zeros(2 * nb_points + len(self.indicesRight) + len(self.indicesFlat) + len(self.indicesHrObt) + len(self.indicesHrAig))
        for i, p in enumerate(unik_points):
            self.Y[2*i] = p[0]
            self.Y[2*i+1] = p[1]
        offset = 2 * nb_points + len(self.indicesRight) + len(self.indicesFlat)
        for i, t in enumerate(self.indicesHrAig):
            v1, v2 = self.get_vecs_around(t, unik_points)
            d = np.linalg.norm(v1) * np.linalg.norm(v2) * np.cos(np.pi / 4)
            self.Y[offset + i] = d
        offset = 2 * nb_points + len(self.indicesRight) + len(self.indicesFlat) + len(self.indicesHrAig)
        for i, t in enumerate(self.indicesHrObt):
            v1, v2 = self.get_vecs_around(t, unik_points)
            d = np.linalg.norm(v1) * np.linalg.norm(v2) * np.cos(3 * np.pi / 4)
            self.Y[offset + i] = d

    # B = Y - S(Xcourant)
    def get_B(self, points):
        nb_points = len(points)
        S = np.zeros(2 * nb_points + len(self.indicesRight) + len(self.indicesFlat) + len(self.indicesHrObt) + len(self.indicesHrAig))
        for i, p in enumerate(points):
            S[2*i] = p[0]
            S[2*i+1] = p[1]
        offset = 2 * nb_points
        for i, t in enumerate(self.indicesRight):
            v1, v2 = self.get_vecs_around(t, points)
            d = v1.dot(v2) 
            S[offset + i] = d
        offset = 2 * nb_points + len(self.indicesRight)
        for i, t in enumerate(self.indicesFlat):
            v1, v2 = self.get_vecs_around(t, points)
            d = np.cross(v1, v2).item(0) 
            S[offset + i] = d
        offset = 2 * nb_points + len(self.indicesRight) + len(self.indicesFlat)
        for i, t in enumerate(self.indicesHrAig):
            v1, v2 = self.get_vecs_around(t, points)
            d = v1.dot(v2) 
            S[offset + i] = d
        offset = 2 * nb_points + len(self.indicesRight) + len(self.indicesFlat) + len(self.indicesHrAig)
        for i, t in enumerate(self.indicesHrObt):
            v1, v2 = self.get_vecs_around(t, points)
            d = v1.dot(v2) 
            S[offset + i] = d
        return self.Y - S

    # Weight Matrix
    # n = 2 * nb_points + indicesRight.size() + indicesFlat.size() + indicesHrAig.size() + indicesHrObt.size()
    def get_P(self):
        nb_points = len(self.point_shapes)
        nb_rights, nb_flats =  len(self.indicesRight), len(self.indicesFlat)
        nb_half_rights = len(self.indicesHrAig) + len(self.indicesHrObt)
        wfix = np.full(2*nb_points, self.poidsPtfFixe)
        wRight = np.full(nb_rights, self.poids90)
        wFlat = np.full(nb_flats, self.poids0)
        wHr = np.full(nb_half_rights, self.poids45)
        self.P = np.diag(np.concatenate((wfix, wRight, wFlat, wHr)))


    ## new vectors
    def partial_derivatives_dotp(self, points, indices):
        nb_points = len(points)
        nb_indices = len(indices)
        m = np.zeros((nb_indices, 2*nb_points))
        for i, t in enumerate(indices):
            idx_prec, idx, idx_suiv = t[0], t[1], t[2]
            pr, p, s = points[t[0]], points[t[1]], points[t[2]]
            # df en Xi-1, Yi-1
            dfx = p[0] - s[0]
            dfy = p[1] - s[1]
            m[i][2*idx_prec] = dfx
            m[i][2*idx_prec + 1] = dfy
            # df en Xi, Yi
            dfx = s[0] - 2*p[0] + pr[0]
            dfy = s[1] - 2*p[1] + pr[1]
            m[i][2*idx] = dfx
            m[i][2*idx + 1] = dfy
            # df en Xi+1, Yi+1
            dfx = p[0] - pr[0]
            dfy = p[1] - pr[1]
            m[i][2*idx_suiv] = dfx
            m[i][2*idx_suiv + 1] = dfy
        return m

    def partial_derivatives_cross(self, points, indices):
        nb_points = len(points) #- 1
        nb_indices = len(indices)
        m = np.zeros((nb_indices, 2*nb_points))
        for i, t in enumerate(indices):
            idx_prec, idx, idx_suiv = t[0], t[1], t[2]
            pr, p, s = points[t[0]], points[t[1]], points[t[2]]
            # df en Xi-1, Yi-1
            dfx = p[1] - s[1]
            dfy = -p[0] + s[0]
            m[i][2*idx_prec] = dfx
            m[i][2*idx_prec + 1] = dfy
            # df en Xi, Yi
            dfx = s[1] - pr[1]
            dfy = -s[0] + pr[0]
            m[i][2*idx] = dfx
            m[i][2*idx + 1] = dfy
            # df en Xi+1, Yi+1
            dfx = -p[1] + pr[1]
            dfy = p[0] - pr[0]
            m[i][2*idx_suiv] = dfx
            m[i][2*idx_suiv + 1] = dfy
        return 


    def get_A(self, points):
        nb_points = len(points) #- 1
        id = np.identity(2 * nb_points)
        partialR = self.partial_derivatives_dotp(points, self.indicesRight)
        partialCross = self.partial_derivatives_cross(points, self.indicesFlat)
        partialHr1 = self.partial_derivatives_dotp(points, self.indicesHrAig)
        partialHr2 = self.partial_derivatives_dotp(points, self.indicesHrObt)
        a = np.vstack((id, partialR))
        if(partialCross != None):
            a = np.vstack((a, partialCross))
        if(partialHr1 != None):
            a = np.vstack((a, partialHr1))
        if(partialHr2 != None):
            a = np.vstack((a, partialHr2))
        return a

    def compute_dx(self, points):
        A = self.get_A(points)
        B = self.get_B(points)
        atp = A.T @ self.P 
        atpa = atp @ A
        atpb = atp @ B
        #dx = np.linalg.lstsq(atpa, atpb)
        #dx = np.linalg.inv(atpa) @ atpb
        dx = np.linalg.solve(atpa, atpb)
        return dx
    
    def prepare_square(self, shapes):
        if len(shapes) == 0:
            return np.array([])
        self.geom_type = shapes[0].geom_type
        self.build_dict_of_unique_points(shapes)
        self.build_pindex_for_shapes(shapes)
        unik_points = list(self.point_shapes)
        self.idx_angles_remarquables(unik_points)
        self.get_Y(unik_points)
        self.get_P()
        return np.array(unik_points)
    
    def square(self, shapes):
        """squares a collection of shapely multilinestrings or polygons
        returns a numpy array of the points after the least square process
        """
        points = self.prepare_square(shapes)
        nb_points = len(points)
        for i in range(self.MAX_ITER):
            dx = self.compute_dx(points)
            points += dx.reshape((nb_points, 2))
            print(i, np.linalg.norm(dx, ord=np.inf))
            if np.linalg.norm(dx, ord=np.inf) < self.NORM_DIFF_TOL:
                break
        self.nb_iters = i
        return points


    # rebuild shapes with updated points from least square process
    def get_shapes_from_new_points(self, original_shapes, new_points):
        """rebuild a list of coordinates from the original collection  of shapes
        and the points obtained from the square process
        """
        unik_points = list(self.point_shapes)
        new_s = []
        for l in original_shapes:
            #coords, is_poly = (l[0].coords, False) if l.geom_type == 'MultiLineString' else (l.exterior.coords, True)
            coords = get_coords(l)
            is_poly = True if self.geom_type == 'Polygon' else False
            size = len(coords)
            new_s.append(np.zeros((size, 2)) )
        for idx_p, p in enumerate(unik_points):
            index_of_lines = self.point_shapes[p] # point_lines_idx[p]
            #print(index_of_lines)
            for idx_l in index_of_lines:
                r = self.get_rank_point_in_shape(idx_p, idx_l)
                #print(idx_l, r, new_points[idx_p])
                new_s[idx_l][r] = np.array(new_points[idx_p])
                if r == 0 and is_poly:
                    new_s[idx_l][-1] = np.array(new_points[idx_p])
        return new_s



if __name__ == '__main__':
    from shapely.wkt import loads
    from shapely.geometry import Polygon, LineString
    import geopandas


    zipfile = "zip://C:/Users/gtouya/workspace/CartAGen4Py/data/test_squaring.zip"
    df = geopandas.read_file(zipfile)
    polygons = df.geometry

    #lines = [loads(wkt)]
    sq = Squarer(pfixe=5)
    with np.printoptions(precision=3, suppress=True):
        points = sq.square(polygons)

    new_s = sq.get_shapes_from_new_points(polygons, points)
    print(new_s)