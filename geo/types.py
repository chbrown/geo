from geo.spatial import polygon_contains
import json


class GeoEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__geo_interface__'):
            return obj.__geo_interface__
        return super(GeoEncoder, self).default(obj)


class BoundingBox(object):
    '''
    BoundingBox(minimum_longitude, minimum_latitude, maximum_longitude, maximum_latitude)

    minimum_longitude = float # western-most coordinate
    minimum_latitude = float  # southern-most coordinate
    maximum_longitude = float # eastern-most coordinate
    maximum_latitude = float  # northern-most coordinate

    # longitude is the easting coordinate, along the x-axis
    # latitude is the northing coordinate, along the y-axis
    '''
    min_x = None
    min_y = None
    max_x = None
    max_y = None

    def __init__(self, min_x, min_y, max_x, max_y):
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y

    def contains(self, x, y):
        '''
        Check whether the given point lies within this box's boundaries

        x = lon = easting coordinate
        y = lat = northing coordinate
        '''
        return (self.min_x <= x <= self.max_x) and (self.min_y <= y <= self.max_y)

    def __str__(self):
        return 'SW: [%0.7f, %0.7f] NE: [%0.7f, %0.7f]' % (self.min_x, self.min_y, self.max_x, self.max_y)

    @property
    def __geo_interface__(self):
        # GeoJSON bbox format
        return [self.min_x, self.min_y, self.max_x, self.max_y]

    @classmethod
    def from_polygons(cls, *polygons):
        # polygons should be a list of lists of points
        xs, ys = zip(*[(x, y) for polygon in polygons for x, y in polygon])
        return cls(min(xs), min(ys), max(xs), max(ys))


class Feature(object):
    '''
    Feature(geometry, properties, id=None, bbox=None)

    A Feature has a geometry that is usually a Polygon or MultiPolygon

    bbox = BoundingBox object (if blank, computed from given polygons)
    '''
    def __init__(self, geometry, properties, id=None, bbox=None):
        self.geometry = geometry
        self.properties = properties
        self.id = id
        self.bbox = bbox

    def contains(self, x, y):
        # first, do coarse-grained check (by bounding box)
        if self.bbox is None or self.bbox.contains(x, y):
            # then the exact check (could be quite slow!)
            # TODO: check for holes (by looking at all linear rings in a polygon
            if self.geometry['type'] == 'MultiPolygon':
                for linear_rings in self.geometry['coordinates']:
                    if polygon_contains(linear_rings[0], x, y):
                        return True
            elif self.geometry['type'] == 'Polygon':
                linear_rings = self.geometry['coordinates']
                if polygon_contains(linear_rings[0], x, y):
                    return True
            else:
                return False
        return False

    @property
    def __geo_interface__(self):
        # GeoJSON Feature format
        geojson = dict(type='Feature', geometry=self.geometry, properties=self.properties)
        if self.bbox:
            geojson['bbox'] = self.bbox
        if self.id:
            geojson['id'] = self.id
        return geojson


class FeatureCollection(object):
    '''
    Helper class to make geolocating lat-lon pairs easier.
    '''
    def __init__(self, features):
        self.features = features

    @property
    def __geo_interface__(self):
        return dict(type='FeatureCollection', features=self.features)

    def features_containing(self, lon, lat):
        # lon = x = easting
        # lat = y = northing
        # TODO: reorder areas into the most popular first so that we find them quicker
        for feature in self.features:
            if feature.contains(lon, lat):
                yield feature

    def first_feature_containing(self, lon, lat):
        for feature in self.features_containing(lon, lat):
            return feature

    def __getitem__(self, feature_id):
        '''
        Access features in this collection by id. E.g.,

            us_states['Ohio']

        '''
        for feature in self.features:
            if feature.id == feature_id:
                return feature
        raise IndexError(feature_id)
