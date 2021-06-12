# encoding: utf-8

import os
import stat
import sys
import re

from fablab_lib import *
from PIL import Image


class TsfFileEffectMixin:

    def initialize_tsf(self, options, w=0, h=0, offset_x=0, offset_y=0, jobname=None, output=sys.stdout):
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
        if(jobname):
            self.header['JobName'] = jobname
        self.offset_x, self.offset_y = float(offset_x), float(offset_y)
        self.header['Size'] = (self.toMm(w), self.toMm(h))
        self.out = output
        self.picture = False

        # header size is in mm this is size converted to pixels
        self.px_widh = int(round(self.svg.uutounit(w, 'in') * options.resolution))
        self.px_height = int(round(self.svg.uutounit(h, 'in') * options.resolution))

    def toDots(self, val):
        return int(round(self.svg.uutounit(val, 'in') * self.header.get('Resolution')))

    def toMm(self, val):
        return self.svg.uutounit(val, 'mm')

    def _simple_header_out(self, name, default):
        self.out.write('<%s: %s>\n' % (name, self.header.get(name, default)))

    def write_tsf_header(self):
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

        self.out.write("<MaterialGroup: %s>\n" % self.header.get('MaterialGroup', 'Standard'))
        self.out.write("<MaterialName: %s>\n" % self.header.get('MaterialName', 'Standard'))

        jobname = re.sub(r'[^\x00-\x7F]','#', self.header.get('JobName', 'job'))
        self.out.write("<JobName: %s>\n" % jobname)

        self._simple_header_out('JobNumber', '2')
        self._simple_header_out('Resolution', '500')
        self._simple_header_out('Cutline', 'none')
        self.out.write('<EndGroup: Header>\n')

    def write_tsf_picture(self, image_path):
        self.picture = True
        if image_path is not None and os.path.isfile(image_path) and os.stat(image_path)[stat.ST_SIZE]:
            self.out.write('<BegGroup: Bitmap>\n')
            self.out.write('<STBmp: 0;0>')
            with open(image_path, 'rb') as image:
                self.out.write(image.read())
            self.out.write('<EOBmp>\n')
            self.out.write('<EndGroup: Bitmap>\n')

    @contextmanager
    def draw_tsf_commands(self):
        if self.draw_tsf_commands:
            self.out.write('<BegGroup: DrawCommands>\n')
            yield self._draw_polygon
            self.out.write('<EndGroup: DrawCommands>\n')

    def _draw_polygon(self, r, g, b, points):
        print_("points", points)
        if points and len(points) > 1:
            # Draw Polygones into the tsf file
            o = [len(points), r, g, b]
            for point in ([self.toDots(x - self.offset_x), self.toDots(y - self.offset_y)] for x, y in points):
                o.extend(point)
            self.out.write('<DrawPolygon: %s>\n' % ";".join((str(i) for i in o)))
