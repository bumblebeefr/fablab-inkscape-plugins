#!/usr/bin/env python
# encoding: utf-8
from contextlib import contextmanager
import os
import platform
import sys
import tempfile
import simplestyle
import math
import time

from fablab_lib import *
from fablab_tsf_lib import TsfFile
from fablab_path_lib import Polyline, Segment

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


class TsfEffect(BaseEffect):

    def __init__(self):
        BaseEffect.__init__(self)
        self.OptionParser.add_option('--tabs', action='store', type='string', default='Job')
        self.OptionParser.add_option('--processmode', action='store', type='choice', choices=['None', 'Standard', 'Layer', 'Stamp', 'Relief'], default='None')
        self.OptionParser.add_option('--jobname', action='store', type='string', default='Job')
        self.OptionParser.add_option('--jobnumber', action='store', type='int', default=1)
        self.OptionParser.add_option('--resolution', action='store', type='int', default=500)
        self.OptionParser.add_option('--layernumber', action='store', type='int', default=1)
        self.OptionParser.add_option('--layeradjustement', action='store', type='float', default=0)
        self.OptionParser.add_option('--stampshoulder', action='store', type='choice', choices=['flat', 'medium', 'steep'], default='flat')
        self.OptionParser.add_option('--cutline', action='store', type='choice', choices=['none', 'circular', 'rectangular', 'optimized'], default='none')
        self.OptionParser.add_option('--spoolpath', action='store', type='string', default='')
        self.OptionParser.add_option('--onlyselection', action="store", type='choice', choices=['true', 'false'], default='false')
        self.OptionParser.add_option('--optimize', action="store", type='choice', choices=['true', 'false'], default='false')

    def get_size_and_offset(self, file_path):
        if(self.onlyselected()):
            return inkscape_command('-z', '-W', file_path), inkscape_command('-z', '-H', file_path), inkscape_command('-z', '-X', file_path), inkscape_command('-z', '-Y', file_path)
        else:
            return inkex.unittouu(self.document.getroot().get('width')), inkex.unittouu(self.document.getroot().get('height')), 0, 0

    def generate_bmp(self, tmp_bmp):
        with tmp_file(".png", text=False) as tmp_png:
            with self.as_tmp_svg() as tmp_svg:
                if(self.onlyselected()):
                    inkscape_command(tmp_svg, '-z', '-D', '-b', '#ffffff', '-y', '1', '-d', self.options.resolution, '-e', tmp_png)
                else:
                    inkscape_command(tmp_svg, '-z', '-C', '-b', '#ffffff', '-y', '1', '-d', self.options.resolution, '-e', tmp_png)

                if(self.options.processmode in ['Layer', 'Relief']):
                    #convert_command(tmp_png, '-flip', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'h8x8a,256', '-depth', '8', '-alpha', 'off', '-compress', 'NONE', '-colors', '256', 'BMP3:%s' % tmp_bmp)
                    #convert_command(tmp_png, '-flip', '-level', '0%,100%,4.0', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'o8x8,16', '-depth', '8', '-alpha', 'off', '-compress', 'NONE', '-colors', '256', 'BMP3:%s' % tmp_bmp)
                    convert_command(tmp_png, '-flip', '-level', '0%,100%,4.0', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'o8x8,16', '-depth', '8', '-alpha', 'off', '-remap', os.path.join(os.getcwd(), 'fablab_grayscale.bmp'), '-compress', 'NONE', 'BMP3:%s' % tmp_bmp)

                else:
                    #convert_command(tmp_png, '-flip', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'h8x8a,256', '-depth', '8', '-alpha', 'off', '-compress', 'NONE', '-colors', '256', 'BMP3:%s' % tmp_bmp)
                    #convert_command(tmp_png, '-flip', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'h4x4a', '-monochrome', '-depth', '1', '-alpha', 'off', '-compress', 'NONE', '-colors', '2', 'BMP3:%s' % tmp_bmp)
                    convert_command(tmp_png, '-flip', '-level', '0%,100%,4.0', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'o8x8', '-remap', os.path.join(os.getcwd(), 'fablab_monochrome.bmp'), '-compress', 'NONE', 'BMP3:%s' % tmp_bmp)

    def onlyselected(self):
        return self.selected and self.options.onlyselection == 'true'

    def job_filepath(self, w, h):
        filepath = os.path.join(self.options.spoolpath, "%s_%sx%s.tsf" % (self.options.jobname, int(math.ceil(float(w))), int(math.ceil(float(h)))))
        cnt = 1
        while(os.path.isfile(filepath)):
            cnt += 1
            filepath = os.path.join(self.options.spoolpath, "%s_%sx%s_%s.tsf" % (self.options.jobname, int(math.ceil(float(w))), int(math.ceil(float(h))), cnt))
        return filepath

    def paths_to_unit_segments(self, path_nodes):
        print_("paths_to_unit_segments", path_nodes)
        if self.options.optimize == 'false':
            for path in path_nodes:
                for points in path_to_segments(path):
                    print_("Mini segments : ", points)
                    yield points
        else:# optimise
            #for polyline in Polyline.generate_from_segments(Segment.convertToSegmentSet(path_nodes)):
            for polyline in Polyline.generate_from_segment_array(list(Segment.convertToSegmentSet(path_nodes))):
                for points in pathd_to_segments(polyline.format()):
                    print_("Mini segments : ", points)
                    yield points

    def effect(self):
        start_time = time.time()
        ink_args = []

        if(self.options.spoolpath):
            if not os.path.isdir(self.options.spoolpath):
                inkex.errormsg(u"Le chemin spécifié (%s) pour le répértoire de spool où seront exportés les fichier tsf est incorrect." % self.options.spoolpath)
                return

        # remove all objects not in selection
        if(self.onlyselected()):
            for k in self.selected:
                ink_args.append('--select=%s' % k)
            ink_args.append("--verb=EditInvert")
            ink_args.append("--verb=EditDelete")

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

        with self.inkscaped(ink_args) as tmp:
            # get document size to test if path are in visble zone
            doc_width, doc_height, doc_offset_x, doc_offset_y = self.get_size_and_offset(tmp)
            output_file = None

            # start generating tsf
            if self.options.spoolpath:
                filepath = self.job_filepath(doc_width, doc_height)
                output_file = open(filepath, "w")
                tsf = TsfFile(self.options, doc_width, doc_height, doc_offset_x, doc_offset_y, output=output_file)
            else:
                tsf = TsfFile(self.options, doc_width, doc_height, doc_offset_x, doc_offset_y)

            tsf.write_header()

            #get paths to cut from file, store them by color
            paths_by_color = {}
            for path in self.document.getroot().iterdescendants("{http://www.w3.org/2000/svg}path"):
                path_style = simplestyle.parseStyle(path.get('style', ''))
                path_color = path_style.get('stroke', None)
                if path_color in TROTEC_COLORS:
                    xmin, xmax, ymin, ymax = simpletransform.computeBBox([path])
                    if all([xmin >= 0, ymin >= 0, xmax <= doc_width, ymax <= doc_height]):
                        path_style['stroke-opacity'] = '0'
                        path.set('style', simplestyle.formatStyle(path_style))
                        paths_by_color.setdefault(path_color, []).append(path)

            # generate png then bmp for engraving
            if(self.options.processmode != 'None'):
                with tmp_file(".bmp", text=False) as tmp_bmp:
                    self.generate_bmp(tmp_bmp)
                    if(identify_command('-format', '%k', tmp_bmp).strip() != "1"):  # If more than one color in png output
                        tsf.write_picture(tmp_bmp)

            # adding polygones
            with tsf.draw_commands() as draw_polygon:
                for path_color in paths_by_color:
                    r, g, b = simplestyle.parseColor(path_color)
                    print_('paths_by_color[path_color]', paths_by_color[path_color])
                    for points in self.paths_to_unit_segments(paths_by_color[path_color]):
                        draw_polygon(r, g, b, points)

            end_time = time.time()

            inkex.errormsg(u"========= Génération du fichier TSF effectuée. =========\n")
            inkex.errormsg(u" - Dimensions : %s mm" % "x".join([str(round(s, 2)) for s in tsf.header.get('Size')]))
            if(tsf.picture):
                inkex.errormsg(u" - Gravure : %s" % tsf.header.get('ProcessMode'))
            else:
                inkex.errormsg(u" - Gravure : Aucune")
            inkex.errormsg(u" - Nombre de couleurs : %s" % len(paths_by_color.keys()))
            inkex.errormsg(u"\n Export effectué en %ss" % round(end_time - start_time,1))

            if output_file:
                try:
                    output_file.close()
                except OSError:
                    pass
            else:
                inkex.errormsg(u"\n Cliquer sur valider pour terminer l'enregistrement du fichier.")


if __name__ == '__main__':
    TsfEffect().affect(output=False)
