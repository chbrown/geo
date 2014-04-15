class Editor(Writer):
    def __init__(self, shapefile=None, shapeType=POINT, autoBalance=1):
        self.autoBalance = autoBalance
        if not shapefile:
            Writer.__init__(self, shapeType)
        elif is_string(shapefile):
            base = os.path.splitext(shapefile)[0]
            if os.path.isfile("%s.shp" % base):
                r = Reader(base)
                Writer.__init__(self, r.shapeType)
                self._shapes = r.shapes()
                self.fields = r.fields
                self.records = r.records()

    def select(self, expr):
        """Select one or more shapes (to be implemented)"""
        # TODO: Implement expressions to select shapes.
        pass

    def delete(self, shape=None, part=None, point=None):
        """Deletes the specified part of any shape by specifying a shape
        number, part number, or point number."""
        # shape, part, point
        if shape and part and point:
            del self._shapes[shape][part][point]
        # shape, part
        elif shape and part and not point:
            del self._shapes[shape][part]
        # shape
        elif shape and not part and not point:
            del self._shapes[shape]
        # point
        elif not shape and not part and point:
            for s in self._shapes:
                if s.shapeType == 1:
                    del self._shapes[point]
                else:
                    for part in s.parts:
                        del s[part][point]
        # part, point
        elif not shape and part and point:
            for s in self._shapes:
                del s[part][point]
        # part
        elif not shape and part and not point:
            for s in self._shapes:
                del s[part]

    def point(self, x=None, y=None, z=None, m=None, shape=None, part=None, point=None, addr=None):
        """Creates/updates a point shape. The arguments allows
        you to update a specific point by shape, part, point of any
        shape type."""
        # shape, part, point
        if shape and part and point:
            try: self._shapes[shape]
            except IndexError: self._shapes.append([])
            try: self._shapes[shape][part]
            except IndexError: self._shapes[shape].append([])
            try: self._shapes[shape][part][point]
            except IndexError: self._shapes[shape][part].append([])
            p = self._shapes[shape][part][point]
            if x: p[0] = x
            if y: p[1] = y
            if z: p[2] = z
            if m: p[3] = m
            self._shapes[shape][part][point] = p
        # shape, part
        elif shape and part and not point:
            try: self._shapes[shape]
            except IndexError: self._shapes.append([])
            try: self._shapes[shape][part]
            except IndexError: self._shapes[shape].append([])
            points = self._shapes[shape][part]
            for i in range(len(points)):
                p = points[i]
                if x: p[0] = x
                if y: p[1] = y
                if z: p[2] = z
                if m: p[3] = m
                self._shapes[shape][part][i] = p
        # shape
        elif shape and not part and not point:
            try: self._shapes[shape]
            except IndexError: self._shapes.append([])

        # point
        # part
        if addr:
            shape, part, point = addr
            self._shapes[shape][part][point] = [x, y, z, m]
        else:
            Writer.point(self, x, y, z, m)
        if self.autoBalance:
            self.balance()

    def validate(self):
        """An optional method to try and validate the shapefile
        as much as possible before writing it (not implemented)."""
        #TODO: Implement validation method
        pass

    def balance(self):
        """Adds a corresponding empty attribute or null geometry record depending
        on which type of record was created to make sure all three files
        are in synch."""
        if len(self.records) > len(self._shapes):
            self.null()
        elif len(self.records) < len(self._shapes):
            self.record()

    def __fieldNorm(self, fieldName):
        """Normalizes a dbf field name to fit within the spec and the
        expectations of certain ESRI software."""
        if len(fieldName) > 11: fieldName = fieldName[:11]
        fieldName = fieldName.upper()
        fieldName.replace(' ', '_')
