from struct import unpack, calcsize
import os

from geo.shapefile import ShapefileException, Array
from geo.shapefile.six import u, b, is_string
from geo.shapefile.shape import Shape


class Reader(object):
    """Reads the three files of a shapefile as a unit or
    separately.  If one of the three files (.shp, .shx,
    .dbf) is missing no exception is thrown until you try
    to call a method that depends on that particular file.
    The .shx index file is used if available for efficiency
    but is not required to read the geometry from the .shp
    file. The "shapefile" argument in the constructor is the
    name of the file you want to open.

    You can instantiate a Reader without specifying a shapefile
    and then specify one later with the load() method.

    Only the shapefile headers are read upon loading. Content
    within each file is only accessed when required and as
    efficiently as possible. Shapefiles are usually not large
    but they can be.
    """
    def __init__(self, *args, **kwargs):
        self.shp = None
        self.shx = None
        self.dbf = None
        self.shapeName = "Not specified"
        self._offsets = []
        self.shpLength = None
        self.numRecords = None
        self.fields = []
        self.__dbfHdrLength = 0
        # See if a shapefile name was passed as an argument
        if len(args) > 0:
            if is_string(args[0]):
                self.load(args[0])
                return
        if "shp" in kwargs.keys():
            if hasattr(kwargs["shp"], "read"):
                self.shp = kwargs["shp"]
                if hasattr(self.shp, "seek"):
                    self.shp.seek(0)
            if "shx" in kwargs.keys():
                if hasattr(kwargs["shx"], "read"):
                    self.shx = kwargs["shx"]
                    if hasattr(self.shx, "seek"):
                        self.shx.seek(0)
        if "dbf" in kwargs.keys():
            if hasattr(kwargs["dbf"], "read"):
                self.dbf = kwargs["dbf"]
                if hasattr(self.dbf, "seek"):
                    self.dbf.seek(0)
        if self.shp or self.dbf:
            self.load()
        else:
            raise ShapefileException("Shapefile Reader requires a shapefile or file-like object.")

    def load(self, shapefile=None):
        """Opens a shapefile from a filename or file-like
        object. Normally this method would be called by the
        constructor with the file object or file name as an
        argument."""
        if shapefile:
            shapeName, ext = os.path.splitext(shapefile)
            self.shapeName = shapeName
            try:
                self.shp = open("%s.shp" % shapeName, "rb")
            except IOError:
                raise ShapefileException("Unable to open %s.shp" % shapeName)
            try:
                self.shx = open("%s.shx" % shapeName, "rb")
            except IOError:
                raise ShapefileException("Unable to open %s.shx" % shapeName)
            try:
                self.dbf = open("%s.dbf" % shapeName, "rb")
            except IOError:
                raise ShapefileException("Unable to open %s.dbf" % shapeName)
        if self.shp:
            self.__shpHeader()
        if self.dbf:
            self.__dbfHeader()

    def __getFileObj(self, f):
        """Checks to see if the requested shapefile file object is
        available. If not a ShapefileException is raised."""
        if not f:
            raise ShapefileException("Shapefile Reader requires a shapefile or file-like object.")
        if self.shp and self.shpLength is None:
            self.load()
        if self.dbf and len(self.fields) == 0:
            self.load()
        return f

    def __restrictIndex(self, i):
        """Provides list-like handling of a record index with a clearer
        error message if the index is out of bounds."""
        if self.numRecords:
            rmax = self.numRecords - 1
            if abs(i) > rmax:
                raise IndexError("Shape or Record index out of range.")
            if i < 0:
                i = range(self.numRecords)[i]
        return i

    def assertFile(self, attr):
        # attr should be 'shp', 'dbf', or 'shx'
        if not getattr(self, attr, None):
            raise ShapefileException("Shapefile Reader requires a shapefile or file-like object."
                "(no %s file found)" % attr)

    def __shpHeader(self):
        """Reads the header information from a .shp or .shx file."""
        if not self.shp:
            raise ShapefileException("Shapefile Reader requires a shapefile or file-like object. (no shp file found")
        shp = self.shp
        # File length (16-bit word * 2 = bytes)
        shp.seek(24)
        self.shpLength = unpack(">i", shp.read(4))[0] * 2
        # Shape type
        shp.seek(32)
        self.shapeType= unpack("<i", shp.read(4))[0]
        # The shapefile's bounding box (lower left, upper right)
        self.bbox = Array('d', unpack("<4d", shp.read(32)))
        # Elevation
        self.elevation = Array('d', unpack("<2d", shp.read(16)))
        # Measure
        self.measure = Array('d', unpack("<2d", shp.read(16)))

    def __shape(self):
        """Returns the header info and geometry for a single shape."""
        f = self.__getFileObj(self.shp)
        record = Shape()
        nParts = nPoints = zmin = zmax = mmin = mmax = None
        (recNum, recLength) = unpack(">2i", f.read(8))
        # Determine the start of the next record
        next = f.tell() + (2 * recLength)
        shapeType = unpack("<i", f.read(4))[0]
        record.shapeType = shapeType
        # For Null shapes create an empty points list for consistency
        if shapeType == 0:
            record.points = []
        # All shape types capable of having a bounding box
        elif shapeType in (3, 5, 8, 13, 15, 18, 23, 25, 28, 31):
            record.bbox = Array('d', unpack("<4d", f.read(32)))
        # Shape types with parts
        if shapeType in (3, 5, 13, 15, 23, 25, 31):
            nParts = unpack("<i", f.read(4))[0]
        # Shape types with points
        if shapeType in (3, 5, 8, 13, 15, 23, 25, 31):
            nPoints = unpack("<i", f.read(4))[0]
        # Read parts
        if nParts:
            record.parts = Array('i', unpack("<%si" % nParts, f.read(nParts * 4)))
        # Read part types for Multipatch - 31
        if shapeType == 31:
            record.partTypes = Array('i', unpack("<%si" % nParts, f.read(nParts * 4)))
        # Read points - produces a list of [x,y] values
        if nPoints:
            record.points = [Array('d', unpack("<2d", f.read(16))) for p in range(nPoints)]
        # Read z extremes and values
        if shapeType in (13, 15, 18, 31):
            (zmin, zmax) = unpack("<2d", f.read(16))
            record.z = Array('d', unpack("<%sd" % nPoints, f.read(nPoints * 8)))
        # Read m extremes and values if header m values do not equal 0.0
        if shapeType in (13, 15, 18, 23, 25, 28, 31) and not 0.0 in self.measure:
            (mmin, mmax) = unpack("<2d", f.read(16))
            # Measure values less than -10e38 are nodata values according to the spec
            record.m = []
            for m in Array('d', unpack("<%sd" % nPoints, f.read(nPoints * 8))):
                if m > -10e38:
                    record.m.append(m)
                else:
                    record.m.append(None)
        # Read a single point
        if shapeType in (1, 11, 21):
            record.points = [Array('d', unpack("<2d", f.read(16)))]
        # Read a single Z value
        if shapeType == 11:
            record.z = unpack("<d", f.read(8))
        # Read a single M value
        if shapeType in (11, 21):
            record.m = unpack("<d", f.read(8))
        # Seek to the end of this record as defined by the record header because
        # the shapefile spec doesn't require the actual content to meet the header
        # definition.  Probably allowed for lazy feature deletion.
        f.seek(next)
        return record

    def __shapeIndex(self, i=None):
        """Returns the offset in a .shp file for a shape based on information
        in the .shx index file."""
        shx = self.shx
        if not shx:
            return None
        if not self._offsets:
            # File length (16-bit word * 2 = bytes) - header length
            shx.seek(24)
            shxRecordLength = (unpack(">i", shx.read(4))[0] * 2) - 100
            numRecords = shxRecordLength // 8
            # Jump to the first record.
            shx.seek(100)
            for r in range(numRecords):
                # Offsets are 16-bit words just like the file length
                self._offsets.append(unpack(">i", shx.read(4))[0] * 2)
                shx.seek(shx.tell() + 4)
        if not i == None:
            return self._offsets[i]

    def shape(self, i=0):
        """Returns a shape object for a shape in the the geometry
        record file."""
        shp = self.__getFileObj(self.shp)
        i = self.__restrictIndex(i)
        offset = self.__shapeIndex(i)
        if not offset:
            # Shx index not available so iterate the full list.
            for j, k in enumerate(self.iterShapes()):
                if j == i:
                    return k
        shp.seek(offset)
        return self.__shape()

    def shapes(self):
        """
        Yield all shapes in the shapefile.
        """
        shp = self.__getFileObj(self.shp)
        # Found shapefiles which report incorrect
        # shp file length in the header. Can't trust
        # that so we seek to the end of the file
        # and figure it out.
        shp.seek(0, 2)
        self.shpLength = shp.tell()
        shp.seek(100)
        while shp.tell() < self.shpLength:
            yield self.__shape()

    def __dbfHeaderLength(self):
        """Retrieves the header length of a dbf file header."""
        if not self.__dbfHdrLength:
            self.assertFile('dbf')
            self.numRecords, self.__dbfHdrLength = unpack("<xxxxLH22x", self.dbf.read(32))
        return self.__dbfHdrLength

    def __dbfHeader(self):
        """Reads a dbf header. Xbase-related code borrows heavily from ActiveState Python Cookbook Recipe 362715 by Raymond Hettinger"""
        self.assertFile('dbf')
        headerLength = self.__dbfHeaderLength()
        numFields = (headerLength - 33) // 32
        for field in range(numFields):
            fieldDesc = list(unpack("<11sc4xBB14x", self.dbf.read(32)))
            name = 0
            idx = 0
            if b("\x00") in fieldDesc[name]:
                idx = fieldDesc[name].index(b("\x00"))
            else:
                idx = len(fieldDesc[name]) - 1
            fieldDesc[name] = fieldDesc[name][:idx]
            fieldDesc[name] = u(fieldDesc[name])
            fieldDesc[name] = fieldDesc[name].lstrip()
            fieldDesc[1] = u(fieldDesc[1])
            self.fields.append(fieldDesc)
        terminator = self.dbf.read(1)
        assert terminator == b("\r")
        self.fields.insert(0, ('DeletionFlag', 'C', 1, 0))

    def __recordFmt(self):
        """Calculates the size of a .shp geometry record."""
        if not self.numRecords:
            self.__dbfHeader()
        fmt = ''.join(['%ds' % fieldinfo[2] for fieldinfo in self.fields])
        fmtSize = calcsize(fmt)
        return (fmt, fmtSize)

    def __record(self):
        """Reads and returns a dbf record row as a list of values."""
        f = self.__getFileObj(self.dbf)
        recFmt = self.__recordFmt()
        recordContents = unpack(recFmt[0], f.read(recFmt[1]))
        if recordContents[0] != b(' '):
            # deleted record
            return None
        record = []
        for (name, typ, size, deci), value in zip(self.fields, recordContents):
            if name == 'DeletionFlag':
                continue
            elif not value.strip():
                record.append(value)
                continue
            elif typ == "N":
                value = value.replace(b('\0'), b('')).strip()
                if value == b(''):
                    value = 0
                elif deci:
                    value = float(value)
                else:
                    value = int(value)
            elif typ == b('D'):
                try:
                    y, m, d = int(value[:4]), int(value[4:6]), int(value[6:8])
                    value = [y, m, d]
                except:
                    value = value.strip()
            elif typ == b('L'):
                value = (value in b('YyTt') and b('T')) or (value in b('NnFf') and b('F')) or b('?')
            else:
                value = u(value)
                value = value.strip()
            record.append(value)
        return record

    def record(self, i=0):
        """Returns a specific dbf record based on the supplied index."""
        f = self.__getFileObj(self.dbf)
        if not self.numRecords:
            self.__dbfHeader()
        i = self.__restrictIndex(i)
        recSize = self.__recordFmt()[1]
        f.seek(0)
        f.seek(self.__dbfHeaderLength() + (i * recSize))
        return self.__record()

    def records(self):
        """
        Yield all records in the dbf file.
        Wrap with list() if you want a list.
        """
        if not self.numRecords:
            self.__dbfHeader()
        f = self.__getFileObj(self.dbf)
        f.seek(self.__dbfHeaderLength())
        for i in xrange(self.numRecords):
            r = self.__record()
            if r:
                yield r

    @property
    def field_names(self):
        return [field_name for field_name, _, _, _ in self.fields[1:]]
