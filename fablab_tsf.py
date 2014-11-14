#!/usr/bin/env python
# encoding: utf-8
import sys
import os
import inkex
import tempfile
import simpletransform
import simplepath
import cubicsuperpath
import simplepath
import simplestyle
import cspsubdiv
import bezmisc

from fablab_sh_lib import inkscape
from fablab_sh_lib import convert

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


def print_(*arg):
    f = open("fablab_debug.log", "a")
    for s in arg:
        s = str(unicode(s).encode('unicode_escape')) + " "
        f.write(s)
    f.write("\n")
    f.close()


def path_to_segments(node):
    mat = simpletransform.composeParents(node, [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    d = node.get('d')

    if len(simplepath.parsePath(d)) == 0:
        return

    p = cubicsuperpath.parsePath(d)
    simpletransform.applyTransformToPath(mat, p)

    # p is now a list of lists of cubic beziers [ctrl p1, ctrl p2, endpoint]
    # where the start-point is the last point in the previous segment

    for sp in p:
        path = []
        subdivideCubicPath(sp, 0.2)  # TODO: smoothness preference
        for csp in sp:
            path.append([csp[1][0], csp[1][1]])
        yield path


def subdivideCubicPath(sp, flat, i=1):
    """
    Break up a bezier curve into smaller curves, each of which
    is approximately a straight line within a given tolerance
    (the "smoothness" defined by [flat]).

    This is a modified version of cspsubdiv.cspsubdiv(). I rewrote the recursive
    call because it caused recursion-depth errors on complicated line segments.
    """

    while True:
        while True:
            if i >= len( sp ):
                return

            p0 = sp[i - 1][1]
            p1 = sp[i - 1][2]
            p2 = sp[i][0]
            p3 = sp[i][1]

            b = (p0, p1, p2, p3)

            if cspsubdiv.maxdist(b) > flat:
                break

            i += 1

        one, two = bezmisc.beziersplitatt(b, 0.5)
        sp[i - 1][2] = one[1]
        sp[i][0] = two[2]
        p = [one[2], one[3], two[1]]
        sp[i:1] = [p]


class DrawPolygon:
    def __init__(self, r, g, b, points=[]):
        self.colors = (r, g, b)
        self.points = points

    def output(self):
        o = [len(self.points)]
        o.extend(self.colors)
        for pt in self.points:
            o.extend(pt)
        return '<DrawPolygon: %s>\n' % ";".join((str(i) for i in o))

    def add_point(self, x, y):
        self.points.append([x, y])


class TsfFile:
    def __init__(self, options, output=sys.stdout):
        self.header = {
            'ProcessMode': options.processmode,
            'Size': (10.0, 10.0),
            'MaterialGroup': 'Standard',
            'MaterialName': 'Standard',
            'JobName': options.jobname,
            'JobNumber': options.jobnumber,
            'Resolution': options.resolution,
            'Cutline': options.cutline,
            'LayerParameters': (options.layernumber, options.layeradjustement),
            'StampShoulder': options.stampshoulder
        }
        self.image = None
        self.draw_commands = []
        self.out = output

    def setSize(self, w, h):
        self.header['Size'] = (self.toMm(w), self.toMm(h))

    def setImage(self, image):
        self.image = image

    def toDots(self, val):
        return int(round(1.0 * inkex.uutounit(inkex.unittouu(str(val)), 'in') * self.header.get('Resolution')))

    def toMm(self, val):
        return inkex.uutounit(inkex.unittouu(str(val)), 'mm')

    def simple_header_out(self, name, default):
        self.out.write('<%s: %s>/n' % (name, self.header.get(name, default)))

    def output(self):
        self.out.write('<!-- Version: 9.4.2.1034>\n')
        self.out.write('<!-- PrintingApplication: inkscape.exe>\n')

        self.out.write('<BegGroup: Header>\n')
        if self.header.get('ProcessMode', "default") == 'None':
            self.out.write('<ProcessMode: Standard>\n')
        else:
            self.simple_header_out('ProcessMode', 'Standard')

        self.out.write('<Size: %s;%s>\n' % self.header.get('Size', (0.0, 0.0)))

        if self.header.get('ProcessMode') == 'Layer':
            self.out.write("<LayerParameter: %s;%s>\n" % self.header.get('LayerParameters', (2, 0.0)))

        if self.header.get('ProcessMode') == 'Stamp':
            self.out.write("<StampShoulder: %s>\n" % self.header.get('StampShoulder', 'flat'))

        self.simple_header_out('MaterialGroup', 'Standard')
        self.simple_header_out('MaterialName', 'Standard')
        self.simple_header_out('JobName', 'bbb_sq10')
        self.simple_header_out('JobNumber', '2')
        self.simple_header_out('Resolution', '500')
        self.simple_header_out('Cutline', 'none')
        self.out.write('<EndGroup: Header>\n')

        if self.header.get('ProcessMode') != 'None' and self.image is not None and os.path.isfile(self.image):
            self.out.write('<BegGroup: Bitmap>\n')
            self.out.write('<STBmp: 0;0>')
            with open(self.image, 'rb') as image:
                self.out.write(image.read())
            self.out.write('<EOBmp>/n')
            self.out.write('<EndGroup: Bitmap>n/')

        if self.draw_commands:
            self.out.write('<BegGroup: DrawCommands>/n')
            for draw_command in self.draw_commands:
                self.out.write(draw_command.output())
            self.out.write('<EndGroup: DrawCommands>/n')

    def add_polygon(self, r, g, b, points):
        polygon = DrawPolygon(r, g, b, [[self.toDots(x), self.toDots(y)] for x, y in points])
        self.draw_commands.append(polygon)


class BaseEffect(inkex.Effect):
    ''' Inspired by this example : http://www.janthor.com/sketches/index.php?/archives/5-Inkscape-calling-Inkscape.html :'''
    def __init__(self):
        inkex.Effect.__init__(self)

    def tmp_file_from_document(self):
        fd, tmp = tempfile.mkstemp(".svg", text=True)
        os.close(fd)
        self.document.write(tmp)
        return tmp

    def reload_from_file(self, tmp):
        self.parse(tmp)
        self.getposinlayer()
        self.getselected()
        self.getdocids()


class FlattenEffect(BaseEffect):

    def __init__(self):
        BaseEffect.__init__(self)
        self.OptionParser.add_option('--processmode', action='store', type='choice', choices=[ 'None', 'Standard', 'Layer', 'Stamp', 'Relief'], default='None')
        self.OptionParser.add_option('--jobname', action='store', type='string', default='Job')
        self.OptionParser.add_option('--jobnumber', action='store', type='int', default=1)
        self.OptionParser.add_option('--resolution', action='store', type='int', default=500)
        self.OptionParser.add_option('--layernumber', action='store', type='int', default=1)
        self.OptionParser.add_option('--layeradjustement', action='store', type='float', default=0)
        self.OptionParser.add_option('--stampshoulder', action='store', type='choice', choices=['flat', 'medium', 'steep'], default='flat')
        self.OptionParser.add_option('--cutline', action='store', type='choice', choices=['none', 'circular', 'rectangular', 'optimized'], default='none')

    def effect(self):
        u"""Converts all texts to paths."""
        tmp = self.tmp_file_from_document()
        try:
            ink_args = ["--file", tmp]

            # unlink clones
            for node in self.document.getroot().iterdescendants("{http://www.w3.org/2000/svg}use"):
                ink_args.append('--select=%s' % node.get("id"))
                ink_args.append("--verb=EditUnlinkClone")

            # ungroup groups
            for node in self.document.getroot().iterdescendants("{http://www.w3.org/2000/svg}g"):
                ink_args.append('--select=%s' % node.get("id"))
                ink_args.append("--verb=SelectionUnGroup")

            # convert texts to paths
            for node in self.document.getroot().iterdescendants("{http://www.w3.org/2000/svg}text"):
                ink_args.append('--select=%s' % node.get("id"))
                ink_args.append("--verb=ObjectToPath")

            # ultimate un-group => remove groups generated when converting text to paths
            ink_args.append("--verb=EditSelectAll")
            ink_args.append("--verb=SelectionUnGroup")

            # ultimate object to path, convert last vector objects to paths
            ink_args.append("--verb=EditSelectAll")
            ink_args.append("--verb=ObjectToPath")

            ink_args.append("--verb=FileSave")
            ink_args.append("--verb=FileClose")

            inkscape(*ink_args)
            self.reload_from_file(tmp)

            # get document size to test if path are in visble zone
            doc_width = inkex.unittouu(self.document.getroot().get('width'))
            doc_height = inkex.unittouu(self.document.getroot().get('height'))

            # start generating tsf 
            tsf = TsfFile(self.options)
            tsf.setSize(doc_width, doc_height)

            #adding polygones
            for path in self.document.getroot().iterdescendants("{http://www.w3.org/2000/svg}path"):
                path_style = simplestyle.parseStyle(path.get('style', ''))
                path_color = path_style.get('stroke', None)
                if path_color in TROTEC_COLORS:
                    xmin, xmax, ymin, ymax = simpletransform.computeBBox([path])
                    if xmin < 0 or ymin < 0 or xmax > doc_width or ymax > doc_height:
                        #node.getparent().remove(node)
                        pass
                    else:
                        r, g, b = simplestyle.parseColor(path_color)
                        for points in path_to_segments(path):
                            tsf.add_polygon(r, g, b, points)
                    path_style['stroke'] = 'none'
                    path.set('style', simplestyle.formatStyle(path_style))

            # generate png then bmp for engraving
            if(self.options.processmode != 'None'):
                fd, tmp_png = tempfile.mkstemp(".png", text=False)
                os.close(fd)
                fd, tmp_bmp = tempfile.mkstemp(".bmp", text=False)
                os.close(fd)
                tmp_svg = self.tmp_file_from_document()
                try:
                    inkscape(tmp_svg, '-z', '-C', '-b', '#ffffff', '-y', '1', '-d', 500, '-e', tmp_png)

                    if(self.options.processMode in ['Layer', 'Relief']):
                        convert(tmp_png, '-flip', '-fx', '(r+g+b)/3', '-colorspace', 'Gray', '-ordered-dither', 'h8x8a,256', '-depth', '8', '-alpha', 'off', '-compress', 'NONE', '-colors', '256', 'BMP3:%s' % tmp_bmp)
                    else:
                        convert(tmp_png, '-flip', '-fx', '(r+g+b)/3', '-colorspace', 'Gray', '-ordered-dither', 'h4x4', '-monochrome', tmp_bmp)
                    tsf.setImage(tmp_bmp)
                finally:
                    tsf.output()
                    os.remove(tmp_svg)
                    os.remove(tmp_png)
                    os.remove(tmp_bmp)
            else:
                tsf.output()

        finally:
            pass
            os.remove(tmp)

        inkex.errormsg(u" ☯ Génération du fichier TSF effectuée, cliquer sur valider pour terminer l'enregistrement du fichier.")

if __name__ == '__main__':
    print_(sys.argv)
    FlattenEffect().affect(output=False)