#!/usr/bin/env python
# encoding: utf-8

# These two lines are only needed if you don't put the script directly into
# the installation directory
import sys, copy
import math, operator, itertools
sys.path.append('/usr/share/inkscape/extensions')


import inkex, simplepath, simpletransform, simplestyle


def print_(*arg):
    f = open("fablab_debug.log", "a")
    for s in arg :
        s = str(unicode(s).encode('unicode_escape')) + " "
        f.write( s )
    f.write("\n")
    f.close()


def unsignedLong( signedLongString):
    longColor = long(signedLongString)
    if longColor < 0:
        longColor = longColor & 0xFFFFFFFF
    return longColor

def getColorString(longColor):

    longColor = unsignedLong(longColor)
    hexColor = hex(longColor)[2:-3]
    hexColor = hexColor.rjust(6, '0')
    return '#' + hexColor.upper()


TROTEC_COLORS = [
    '#ff0000',
    '#0000ff',
    '#336699',
    '#00ffff',
    '#00ff00',
    '#009933',
    '#006633',
    '#999933',
    '#996633',
    '#663300',
    '#660066',
    '#9900cc',
    '#ff00ff',
    '#ff6600',
    '#ffff00'
]


# precision to 1/100 px should be sufficient for designs in mm ?
PRECISION = 100.0


def roundValues(arr):
    return [roundValue(val) for val in arr]


def roundValue(val):
    return round(val * PRECISION) / PRECISION


def similar(a, b):
    print_(a, b)
    if type(a) is list and type(b) is list:
        return False not in[similar(c[0], c[1]) for c in zip(a, b)]
    else:
        return abs(roundValue(a) - roundValue(b)) <= 2 / PRECISION


def solve_tsp_dynamic(polylines):
    #calc all lengths
    all_distances = [[x.distance_to(y) for y in polylines] for x in polylines]
    print_("polylines : ", polylines)
    print_("all_distances : ", all_distances)
    #initial value - just distance from 0 to every other point + keep the track of edges
    A = {(frozenset([0, idx+1]), idx+1): (dist, [0,idx+1]) for idx,dist in enumerate(all_distances[0][1:])}
    cnt = len(polylines)
    for m in range(2, cnt):
        B = {}
        for S in [frozenset(C) | {0} for C in itertools.combinations(range(1, cnt), m)]:
            for j in S - {0}:
                B[(S, j)] = min( [(A[(S-{j},k)][0] + all_distances[k][j], A[(S-{j},k)][1] + [j]) for k in S if k != 0 and k!=j]) #this will use 0th index of tuple for ordering, the same as if key=itemgetter(0) used
        A = B
    res = min([(A[d][0] + all_distances[0][d[1]], A[d][1]) for d in iter(A)])
    return res[1]




class Polyline:

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
            Before running, segments in the array must not be flaged 'used'.
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
    def optimize_order(cls, arr):
        last_poly = Origin()
        while len(arr) > 0:
            #print_('*********** Taille du tableau ', len(arr), '***********')
            next_poly = None
            dist = None
            for i, polyline in enumerate(arr):
                #print_('*********** elment ', i, '***********')
                if(next_poly is None):
                    next_poly = polyline
                    dist = last_poly.distance_to(polyline)
 
                #print_("distance",polyline.distance_to(last_poly)," compare a",dist)
                if(last_poly.distance_to(polyline) < dist):
                    next_poly = polyline
                    dist = last_poly.distance_to(polyline)
                    #print_("je prend ",i)
 
                #print_("distance_inverse",polyline.distance_reversed_to(last_poly)," compare a",dist)
                if(last_poly.distance_to_reversed(polyline) < dist):
                    polyline.reverse()
                    next_poly = polyline
                    dist = last_poly.distance_to(polyline)
                    #print_("je prend l'inverse de",i)

            last_poly = next_poly
            arr.remove(next_poly)
            yield next_poly


class Origin(Polyline):

    def __init__(self):
        pass

    def start_point(self):
        return [0, 0]

    def end_point(self):
        return [0,0]

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
    def __init__(self, start, end, command='L', extra_parameters=[]):
        self.start = roundValues(start)
        self.end = roundValues(end)
        self.command = command
        self.extra_parameters = roundValues(extra_parameters)
        self.used = False

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
        if self.command == 'L':
            self.end, self.start = self.start, self.end
        elif self.command == 'C':
            self.end, self.start = self.start, self.end
            self.extra_parameters[:2], self.extra_parameters[2:4] = self.extra_parameters[2:4], self.extra_parameters[:2]
        else:
            inkex.errormsg("Path Command %s can't be reversed Yet" % self.command)

    @classmethod
    def convertToSegments(cls, path):
        path_start = None
        currentPoint = None

        for cmd, params in simplepath.parsePath(path.get('d')):
            if(cmd == 'M'):
                if(path_start is None):
                    path_start = params
                currentPoint = params

            elif(cmd == 'L'):
                yield Segment(currentPoint, params)
                currentPoint = params

            elif (cmd == 'C'):
                yield Segment(currentPoint, params[-2:], command='C', extra_parameters=params[:-2])
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
        #print_("Searchin' next segment starting at %s:" % end)
        for segment in arr:
            #print_("  - Segment %s -> %s (used:%s)" % (segment.start, segment.end, segment.used))
            if not segment.used:
                if segment.end == end:
                    #print_("    reversing..")
                    segment.reverse()
                    #print_("     %s -> %s" % (segment.start, segment.end))
                if segment.start == end:
                    #print_("    !!! Got It !!!\n")
                    segment.used = True
                    return segment
        #print_("Not found :( \n")
        return None



def extract_optimizable_paths_by_color(nodes):
    '''
        nodes doit etre un iterateur sur des noeuds (tableau,generateur,noeud type groupe, ...)
    '''
    print_(nodes)
    for node in nodes:
        
        # Noeuds de type Chemin
        if node.tag == "{http://www.w3.org/2000/svg}path":
             # work on copy to be shure not breaking anything
            p = copy.deepcopy(node)

            # apply transformation info on path, otherwise dealing with transform would be a mess
            simpletransform.fuseTransform(p)

            # get style, check color, ...
            style = simplestyle.parseStyle(p.get('style'))
            color = style.get('stroke', None)

            if(color in TROTEC_COLORS):
                yield color, p
            else:
                inkex.errormsg("%s n'est pas une couleur TROTEC, supposons que c'est quelquechose a graver" %color)
                yield 'engrave', p

        elif node.tag == "{http://www.w3.org/2000/svg}use":
            inkex.errormsg("Les clones ne sont pas geres pour le moment")
            pass
        elif node.tag == "{http://www.w3.org/2000/svg}rect":
            inkex.errormsg("Les rectangles ne sont pas geres pour le moment")
            pass

        # Noeuds de type groupe
        elif node.tag == "{http://www.w3.org/2000/svg}g":
            inkex.errormsg("Les Groupes ne sont pas geres pour le moment")
#             for path in extract_optimizable_paths_by_color(node):
#                 path.set('transform', node.get('transform', ''))
#                 simpletransform.fuseTransform(p)
#                 yield path
            pass

        elif node.tag == "{http://www.w3.org/2000/svg}image":
            inkex.errormsg("Les Images ne sont pas geres pour le moment")
            pass
        else:
            inkex.errormsg("Les noeuds de type %s ne sont pas geres" % node.tag)
            pass


# Pour le moment :
#  - ne prend en entrée que des path (voir a gerer les rectangles au moins)
#  - Les objets doivent être degroupés d'abord


# TODO : Faire une classe Polyline en plus de la de segment et faire plusieur optmisation 
#        de suite pour pouvoir joindre des poliligne non fermées dnas la construction 
#        est partie dans des direction opposées
class MyEffect(inkex.Effect):
    def __init__(self):
        """
        Constructor.
        Defines the "--what" option of a script.
        """
        # Call the base class constructor.
        inkex.Effect.__init__(self)
        self.OptionParser.add_option('--tab')
        self.start_stop = {}

    def effect(self):

        #print_(self.options)
        parent = self.current_layer

        #create a group where we wil write nodes. Determine BoundingBox to mode the  output near the original selection
        #x1, y1, x2, y2 = simpletransform.computeBBox(self.selected.values())
        grp = inkex.etree.SubElement(parent, inkex.addNS('g', 'svg'), {'transform': "translate(%s,%s)" % (200, 200)})#, {'transform': "translate(%s,%s)" % (x2,0)})

        segments_by_color = {}
# 
#         for path in self.selected:
#             print_(self.selected.get(path).tag)

        print_(self.selected)

        for color, path in extract_optimizable_paths_by_color((self.selected.get(n) for n in self.selected)):
            if color not in segments_by_color:
                segments_by_color[color] = set()
            segments_by_color[color].update(Segment.convertToSegments(path))

#         for path in self.selected:
# 
#             # work on copy to be shure not breaking anything
#             p = copy.deepcopy(self.selected.get(path))
# 
#             # apply transformation info on path, otherwise dealing with transform would be a mess
#             simpletransform.fuseTransform(p)
# 
#             # get style, check color, ...
#             style = simplestyle.parseStyle(p.get('style'))
#             color = style.get('stroke', None)
# 
#             if(color in TROTEC_COLORS):
#                 if color not in segments_by_color:
#                     segments_by_color[color] = set()
#                 segments_by_color[color].update(Segment.convertToSegments(p))
#             else:
#                 inkex.errormsg("color %s is not a valid TROTEC color, not managed by this plugin Yet" % color)

        for color in TROTEC_COLORS:
            for poly in Polyline.optimize_order([p for p in Polyline.generate_from_segment_array(segments_by_color.get(color, []))]):
                line_attribs = {'style': "fill:none;stroke:%s;stroke-width:2;marker-end:url(#Arrow2Mend)" % color, 'd': poly.format()}
                inkex.etree.SubElement(grp, inkex.addNS('path', 'svg'), line_attribs)


if __name__ == '__main__':
    effect = MyEffect()
    effect.affect()