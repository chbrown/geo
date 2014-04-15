"""
shapefile.py
Provides read and write support for ESRI Shapefiles.
author: jlawhead<at>geospatialpython.com
date: 20130727
version: 1.2.0
Compatible with Python versions 2.4-3.x
"""
import array


class ShapefileException(Exception):
    """An exception to handle shapefile specific problems."""
    pass

class Array(array.array):
    """Converts python tuples to lits of the appropritate type.
    Used to unpack different shapefile header parts."""
    def __repr__(self):
        return str(self.tolist())

def signed_area(coords):
    """Return the signed area enclosed by a ring using the linear time
    algorithm at http://www.cgafaq.info/wiki/Polygon_Area. A value >= 0
    indicates a counter-clockwise oriented ring.
    """
    xs, ys = map(list, zip(*coords))
    xs.append(xs[1])
    ys.append(ys[1])
    return sum(xs[i]*(ys[i+1]-ys[i-1]) for i in range(1, len(coords)))/2.0
