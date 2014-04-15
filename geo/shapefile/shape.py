from geo.shapefile import signed_area
from geo.shapefile.types import POINT, POINTM, POINTZ
from geo.shapefile.types import MULTIPOINT, MULTIPOINTM, MULTIPOINTZ
from geo.shapefile.types import POLYLINE, POLYLINEM, POLYLINEZ
from geo.shapefile.types import POLYGON, POLYGONM, POLYGONZ


class Shape(object):
    def __init__(self, shapeType=None):
        """Stores the geometry of the different shape types
        specified in the Shapefile spec. Shape types are
        usually point, polyline, or polygons. Every shape type
        except the "Null" type contains points at some level for
        example verticies in a polygon. If a shape type has
        multiple shapes containing points within a single
        geometry record then those shapes are called parts. Parts
        are designated by their starting index in geometry record's
        list of shapes."""
        self.shapeType = shapeType
        self.points = []

    @property
    def __geo_interface__(self):
        if self.shapeType in [POINT, POINTM, POINTZ]:
            return dict(type='Point', coordinates=tuple(self.points[0]))
        elif self.shapeType in [MULTIPOINT, MULTIPOINTM, MULTIPOINTZ]:
            return dict(type='MultiPoint', coordinates=tuple([tuple(p) for p in self.points]))
        elif self.shapeType in [POLYLINE, POLYLINEM, POLYLINEZ]:
            if len(self.parts) == 1:
                return dict(type='LineString', coordinates=tuple([tuple(p) for p in self.points]))
            else:
                ps = None
                coordinates = []
                for part in self.parts:
                    if ps == None:
                        ps = part
                        continue
                    else:
                        coordinates.append(tuple([tuple(p) for p in self.points[ps:part]]))
                        ps = part
                else:
                    coordinates.append(tuple([tuple(p) for p in self.points[part:]]))
                return dict(type='MultiLineString', coordinates=tuple(coordinates))
        elif self.shapeType in [POLYGON, POLYGONM, POLYGONZ]:
            if len(self.parts) == 1:
                return dict(type='Polygon', coordinates=(tuple([tuple(p) for p in self.points]),))
            else:
                ps = None
                coordinates = []
                for part in self.parts:
                    if ps == None:
                        ps = part
                        continue
                    else:
                        coordinates.append(tuple([tuple(p) for p in self.points[ps:part]]))
                        ps = part
                else:
                    coordinates.append(tuple([tuple(p) for p in self.points[part:]]))
                polys = []
                poly = [coordinates[0]]
                for coord in coordinates[1:]:
                    if signed_area(coord) < 0:
                        polys.append(poly)
                        poly = [coord]
                    else:
                        poly.append(coord)
                polys.append(poly)
                if len(polys) == 1:
                    return dict(type='Polygon', coordinates=tuple(polys[0]))
                elif len(polys) > 1:
                    return dict(type='MultiPolygon', coordinates=polys)
