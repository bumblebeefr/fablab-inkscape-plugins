# encoding: utf-8

import os
import sys
import bezmisc
import cspsubdiv
import inkex

from fablab_lib import *


class TsfFile:
    def __init__(self, options, w=0, h=0, offset_x=0, offset_y=0, output=sys.stdout):
        """
            Object to generate a tsf file.

            options : option object used to generate tsf header
            w : width of the job in pixels (inkscape uunit)
            h : height of the job in pixels (inkscape uunit)
            offset_x : offset between the svg x origin and the job origin (useful when we are not extracting the page but only a selection
            offset_y : offset between the svg y origin and the job origin (useful when we are not extracting the page but only a selection
            output : output file stream
        """
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
        self.offset_x, self.offset_y = offset_x, offset_y
        self.header['Size'] = (self.toMm(w), self.toMm(h))
        self.out = output

    def toDots(self, val):
        return int(round(1.0 * inkex.uutounit(inkex.unittouu(str(val)), 'in') * self.header.get('Resolution')))

    def toMm(self, val):
        return inkex.uutounit(inkex.unittouu(str(val)), 'mm')

    def _simple_header_out(self, name, default):
        self.out.write('<%s: %s>\n' % (name, self.header.get(name, default)))

    def write_header(self):
        self.out.write('<!-- Version: 9.4.2.1034>\n')
        self.out.write('<!-- PrintingApplication: inkscape.exe>\n')

        self.out.write('<BegGroup: Header>\n')
        if self.header.get('ProcessMode', "default") == 'None':
            self.out.write('<ProcessMode: Standard>\n')
        else:
            self._simple_header_out('ProcessMode', 'Standard')

        self.out.write('<Size: %s;%s>\n' % self.header.get('Size', (0.0, 0.0)))

        if self.header.get('ProcessMode') == 'Layer':
            self.out.write("<LayerParameter: %s;%s>\n" % self.header.get('LayerParameters', (2, 0.0)))

        if self.header.get('ProcessMode') == 'Stamp':
            self.out.write("<StampShoulder: %s>\n" % self.header.get('StampShoulder', 'flat'))

        self._simple_header_out('MaterialGroup', 'Standard')
        self._simple_header_out('MaterialName', 'Standard')
        self._simple_header_out('JobName', 'bbb_sq10')
        self._simple_header_out('JobNumber', '2')
        self._simple_header_out('Resolution', '500')
        self._simple_header_out('Cutline', 'none')
        self.out.write('<EndGroup: Header>\n')

    def write_picture(self, image_path):
        if image_path is not None and os.path.isfile(image_path):
            self.out.write('<BegGroup: Bitmap>\n')
            self.out.write('<STBmp: 0;0>')
            with open(image_path, 'rb') as image:
                self.out.write(image.read())
            self.out.write('<EOBmp>\n')
            self.out.write('<EndGroup: Bitmap>n/')

    @contextmanager
    def draw_commands(self):
        if self.draw_commands:
            self.out.write('<BegGroup: DrawCommands>\n')
            yield self._draw_polygon
            self.out.write('<EndGroup: DrawCommands>\n')

    def _draw_polygon(self, r, g, b, points):
        o = [len(points), r, g, b]
        for point in ([self.toDots(x - self.offset_x), self.toDots(y - self.offset_x)] for x, y in points):
            o.extend(point)
        self.out.write('<DrawPolygon: %s>\n' % ";".join((str(i) for i in o)))
