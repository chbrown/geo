import sys

PYTHON3 = sys.version_info[0] == 3

if PYTHON3:
    xrange = range

def b(v):
    if PYTHON3:
        if isinstance(v, str):
            # For python 3 encode str to bytes.
            return v.encode('utf-8')
        elif isinstance(v, bytes):
            # Already bytes.
            return v
        else:
            # Error.
            raise Exception('Unknown input type')
    else:
        # For python 2 assume str passed in and return str.
        return v

def u(v):
    if PYTHON3:
        if isinstance(v, bytes):
            # For python 3 decode bytes to str.
            return v.decode('utf-8')
        elif isinstance(v, str):
            # Already str.
            return v
        else:
            # Error.
            raise Exception('Unknown input type')
    else:
        # For python 2 assume str passed in and return str.
        return v

def is_string(v):
    if PYTHON3:
        return isinstance(v, str)
    else:
        return isinstance(v, basestring)
