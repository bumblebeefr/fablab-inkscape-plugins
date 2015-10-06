#!/usr/bin/env python
# encoding: utf-8

import sys
import copy
import math

sys.path.append('/usr/share/inkscape/extensions')
import inkex
import simplepath
import simpletransform


def print_(*arg):
    f = open("fablab_debug.log", "a")
    for s in arg:
        s = str(unicode(s).encode('unicode_escape')) + " "
        f.write(s)
    f.write("\n")
    f.close()


# precision to 1/10 px should be sufficient for designs in mm ?
PRECISION = 10


def update_precision_factor(precision):
    # Not the best way to do it, may need a little bit of refactoring
    # to handle precision correctly with document unit :/
    '''Set precision value. by default 10 for 1/10 precision.'''
    global PRECISION
    PRECISION = precision


def roundValues(arr):
    return [roundValue(val) for val in arr]


def roundValue(val):
    return round(val, int(round(PRECISION)))


def similar(a, b):

    print_(a, b)
    if type(a) is list and type(b) is list:
        return False not in[similar(c[0], c[1]) for c in zip(a, b)]
    else:
        return abs(roundValue(a) - roundValue(b)) <= 2 / PRECISION


class Polyline:

    """
    Basically a  list of consecutive curve segments that form a polyline.
    """

    def __init__(self, initial_segment=None):
        self.segments = [initial_segment]

    def start_point(self):
        return self.segments[0].start

    def end_point(self):
        return self.segments[-1].end

    def append(self, segment):
        if(segment.start == self.end_point()):
            self.segments.append(segment)
        else:
            raise AssertionError("can't add segment that does not start with end_point of the current Polyline")

    def length(self):
        return len(self.segments)

    def to_simplepath(self):
        path = []
        if self.length() > 0:
            path.append(self.segments[0].simplePathStart())
            path.extend((p.simplePathEnd() for p in self.segments))
        return path

    def format(self):
        return simplepath.formatPath(self.to_simplepath())

    def reverse(self):
        self.segments.reverse()
        for segment in self.segments:
            segment.reverse()

    def _contruct_from_segment_array(self, arr):
        while True:
            next_segment = Segment.find_and_flag_next_segment(self.end_point(), arr)
            if(next_segment is not None):
                self.append(next_segment)
            else:
                break

    def distance_to(self, polyline):
        x1, y1 = self.end_point()
        x2, y2 = polyline.start_point()
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def distance_to_reversed(self, polyline):
        x1, y1 = self.end_point()
        x2, y2 = polyline.end_point()
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    @classmethod
    def generate_from_segment_array(cls, arr):
        ''' Generate (yield) polylines(array of consecutive segments) from the specified segment array.
            Before running, segments in the array must not be flaged 'used'. The order of each polyline
            may not minimise the distance beetween each of them, but with this methos polylines shout
            not be cut.
        '''
        for segment in arr:
            if(not segment.used):
                segment.used = True
                polyline = Polyline(segment)
                polyline._contruct_from_segment_array(arr)
                polyline.reverse()
                polyline._contruct_from_segment_array(arr)
                yield polyline

    @classmethod
    def optimize_order(cls, polylines):
        '''
            Generator to sorted polylines in order to minimise distance beetween each of them.
        '''
        arr = list(polylines)
        last_poly = Origin()
        while len(arr) > 0:
            next_poly = None
            dist = None
            for polyline in arr:
                if(next_poly is None):
                    next_poly = polyline
                    dist = last_poly.distance_to(polyline)

                if(last_poly.distance_to(polyline) < dist):
                    next_poly = polyline
                    dist = last_poly.distance_to(polyline)

                if(last_poly.distance_to_reversed(polyline) < dist):
                    polyline.reverse()
                    next_poly = polyline
                    dist = last_poly.distance_to(polyline)

            last_poly = next_poly
            arr.remove(next_poly)
            yield next_poly


class Origin(Polyline):

    """
    Polyline object with only one curve segment that is a line between
    the origin (0,0) and himself.
    """

    def __init__(self):
        pass

    def start_point(self):
        return [0, 0]

    def end_point(self):
        return [0, 0]

    def append(self, segment):
        raise AssertionError("can't add segment to Origin")

    def length(self):
        return 0

    def to_simplepath(self):
        raise AssertionError("can't convert to Origin to simplemath")

    def format(self):
        raise AssertionError("can't convert to Origin to simplemath")

    def reverse(self):
        pass

    def _contruct_from_segment_array(self, arr):
        raise AssertionError("can't add segment to Origin")


class Segment:

    """
    Represent the smallest path element as a curve segment beween
    two points. This can be a line segment or any other type of svg
    curve segment.
    """

    def __init__(self, start, end, command='L', extra_parameters=[]):
        self.start = roundValues(start)
        self.end = roundValues(end)
        self.command = command
        self.pathdefs = simplepath.pathdefs.get(command)
        self.extra_parameters = list(extra_parameters)
        for i, p in enumerate(extra_parameters):
            if(self.pathdefs[3][i] == 'float'):
                self.extra_parameters[i] = roundValue(p)
        self.used = False

    def start_point(self):
        return self.start

    def end_point(self):
        return self.end

    def simplePathStart(self):
        return ['M', self.start]

    def simplePathEnd(self):
        parameters = self.extra_parameters[:]
        parameters.extend(self.end)
        return [self.command, parameters]

    def toSimplePath(self):
        return [self.simplePathStart(), self.simplePathEnd()]

    def formatPath(self):
        return simplepath.formatPath(self.toSimplePath())

    def is_similar_to_segment(self, other):
        return similar(self.start, other.start) and similar(self.end, other.end) and self.command == other.command and similar(self.extra_parameters, other.extra_parameters)

    def __eq__(self, other):
        if(isinstance(other, Segment)):
            if self.is_similar_to_segment(other):
                return True
            inv = copy.deepcopy(self)
            inv.reverse()
            return inv.is_similar_to_segment(other)
        else:
            raise NotImplemented()

    def __hash__(self):
        h = self.command.__hash__()
        for c in self.start:
            h += c.__hash__()
        for c in self.end:
            h += c.__hash__()
        for c in self.extra_parameters:
            h += c.__hash__()
        return h

    def reverse(self):
        if self.command in ['L','Q']:
            self.end, self.start = self.start, self.end
        elif self.command == 'C':
            self.end, self.start = self.start, self.end
            self.extra_parameters[:2], self.extra_parameters[2:4] = self.extra_parameters[2:4], self.extra_parameters[:2]
        elif self.command == 'A':
            self.end, self.start = self.start, self.end
            self.extra_parameters[4] = (self.extra_parameters[4] + 1) % 2
        else:
            inkex.errormsg("Path Command %s can't be reversed Yet" % self.command)

    def distance_to(self, segment):
        x1, y1 = self.end_point()
        x2, y2 = segment.start_point()
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def distance_to_reversed(self, segment):
        x1, y1 = self.end_point()
        x2, y2 = segment.end_point()
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    @classmethod
    def convertToSegmentSet(cls, paths):
        output = set()
        for path in paths:
            output.update(cls.convertToSegments(path))
        return output

    @classmethod
    def convertToSegments(cls, path_node):
        path_start = None
        currentPoint = None

        # work on copy to be shure not breaking anything
        path = copy.deepcopy(path_node)

        # apply transformation info on path, otherwise dealing with transform would be a mess
        simpletransform.fuseTransform(path)

        for cmd, params in simplepath.parsePath(path.get('d')):
            print_('cmd, params', cmd, params)
            if cmd == 'M':
                if(path_start is None):
                    path_start = params
                currentPoint = params

            elif cmd == 'L':
                yield Segment(currentPoint, params)
                currentPoint = params

            elif cmd in ['A', 'Q', 'C']:
                yield Segment(currentPoint, params[-2:], command=cmd, extra_parameters=params[:-2])
                currentPoint = params[-2:]

            elif (cmd == 'Z'):
                # Z is a line between the last point and the start of the shape
                yield Segment(currentPoint, path_start)
                currentPoint = None
                path_start = None

            else:
                inkex.errormsg("Path Command %s not managed Yet" % cmd)

    @classmethod
    def find_and_flag_next_segment(cls, end, arr):
        '''
            Find a segment that can be placed after the 'end' point in the polyline. Can reverse a segment if needed.
            Mark the segment used (Segement.used = True) before returning it.
             - end : last point of the polyline
             - arr : array of segments
        '''
        for segment in arr:
            if not segment.used:
                if segment.end == end:
                    segment.reverse()

                if segment.start == end:
                    segment.used = True
                    return segment

        return None
