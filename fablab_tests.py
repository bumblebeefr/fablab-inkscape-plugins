#!/usr/bin/env python
# encoding: utf-8

# These two lines are only needed if you don't put the script directly into
# the installation directory
import sys, copy
sys.path.append('/usr/share/inkscape/extensions')


import inkex, simplepath, simpletransform, simplestyle


def print_(*arg):
    f = open("fablab_debug.log","a")
    for s in arg :
        s = str(unicode(s).encode('unicode_escape'))+" "
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
def roundValues(arr):
    #return [round(val * 100) / 100 for val in arr]
    return arr


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
        return self.start == other.start and self.end == other.end and self.command == other.command and self.extra_parameters == other.extra_parameters

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
            #outch that's buggy
            inkex.errormsg("Hum on dirait que l'invertion d'une courbe de bezier ne soit pas bonne :(")
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
    def polyline_to_simplepath(cls, poly):
        path = []
        if len(poly) > 0:
            path.append(poly[0].simplePathStart())
            path.extend((p.simplePathEnd() for p in poly))
        return path

    @classmethod
    def format_polyline(cls, poly):
        return simplepath.formatPath(Segment.polyline_to_simplepath(poly))

    @classmethod
    def find_and_flag_next_segment(cls, end, arr):
        '''
            Find a segment that can be placed after the 'end' point in the polyline. Can reverse a segment if needed.
            Mark the segment used (Segement.used = True) before returning it.
             - end : last point of the polyline
             - arr : array of segments
        '''
        print_("Searchin' next segment starting at %s:" % end)
        for segment in arr:
            print_("  - Segment %s -> %s (used:%s)" % (segment.start, segment.end, segment.used))
            if not segment.used:
                if segment.end == end:
                    print_("    reversing..")
                    segment.reverse()
                    print_("     %s -> %s" % (segment.start, segment.end))
                if segment.start == end:
                    print_("    !!! Got It !!!\n")
                    segment.used = True
                    return segment
        print_("Not found :( \n")
        return None

    @classmethod
    def _contruct_polyline(cls, polyline, arr):
        while True:
            next_segment = Segment.find_and_flag_next_segment(polyline[-1].end, arr)
            if(next_segment is not None):
                polyline.append(next_segment)
            else:
                break


    @classmethod
    def polylines_iter(cls, arr):
        ''' Generate (yield) polylines(array of consecutive segments) from the specified segment array.
            Before running, segments in the array must not be flaged 'used'.
        '''
        for segment in arr:
            if(not segment.used):
                segment.used = True
                polyline = [segment]
                Segment._contruct_polyline(polyline, arr)
                if(len(polyline) == 1):
                    #single line ? maybe we start by the wrong side, reversing and retry
                    segment.reverse()
                    Segment._contruct_polyline(polyline, arr)
                yield polyline


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

        for path in self.selected:
            # work on copy to be shure not breaking anything
            p = copy.deepcopy(self.selected.get(path))

            # apply transformation info on path, otherwise dealing with transform would be a mess
            simpletransform.fuseTransform(p)

            # get style, check color, ...
            style = simplestyle.parseStyle(p.get('style'))
            color = style.get('stroke', None)

            if(color in TROTEC_COLORS):
                if color not in segments_by_color:
                    segments_by_color[color] = set()
                segments_by_color[color].update(Segment.convertToSegments(p))
            else:
                inkex.errormsg("color %s is not a valid TROTEC color, not managed by this plugin Yet" % color)

        for color in TROTEC_COLORS:
            for poly in Segment.polylines_iter(segments_by_color.get(color, [])):
                line_attribs = {'style': "fill:none;stroke:%s;stroke-width:2;" % color, 'd': Segment.format_polyline(poly)}
                inkex.etree.SubElement(grp, inkex.addNS('path', 'svg'), line_attribs)

            #for d in [s.formatPath() for s in segments_by_color.get(color, [])]:
            #    line_attribs = {'style': "fill:none;stroke:%s;stroke-width:2;" % color, 'd': d}
            #    inkex.etree.SubElement(grp, inkex.addNS('path', 'svg'), line_attribs)



if __name__ == '__main__':
    effect = MyEffect()
    effect.affect()