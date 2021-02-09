#!/usr/bin/env python
# encoding: utf-8
import os
import simplestyle
import inkex.paths
from inkex.elements import ShapeElement
import inkex.command
import time
import tempfile

from fablab_lib import (
    ImageMagickError, execute_command, execute_async_command, inkscape_command,
    inkscapeX_command, convert_command, identify_command, hex_color,
    tmp_file, print_, path_to_segments, pathd_to_segments, subdivideCubicPath,
    BaseEffect
)
from fablab_tsf_lib import TsfFileEffect
from fablab_path_lib import Polyline, Segment
from fablab_tsf2svg_lib import TsfFilePreviewer
import fablab_path_lib


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


class TsfEffect(BaseEffect, TsfFileEffect):

    def __init__(self):
        BaseEffect.__init__(self)
        self.arg_parser.add_argument(
            '--tabs', action='store', type=str, default='Job')
        self.arg_parser.add_argument(
            '--processmode', action='store', type=str, choices=[
                'None', 'Standard', 'Layer', 'Stamp', 'Relief'
            ], default='None'
        )
        self.arg_parser.add_argument(
            '--jobname', action='store', type=str, default='Job'
        )
        self.arg_parser.add_argument(
            '--jobnumber', action='store', type=int, default=1
        )
        self.arg_parser.add_argument(
            '--resolution', action='store', type=int, default=500
        )
        self.arg_parser.add_argument(
            '--layernumber', action='store', type=int, default=1
        )
        self.arg_parser.add_argument(
            '--layeradjustement', action='store', type=float, default=0
        )
        self.arg_parser.add_argument(
            '--stampshoulder', action='store', type=str,
            choices=['flat', 'medium', 'steep'], default='flat'
        )
        self.arg_parser.add_argument(
            '--cutline', action='store', type=str,
            choices=['none', 'circular', 'rectangular', 'optimized'],
            default='none'
        )
        self.arg_parser.add_argument(
            '--spoolpath', action='store', type=str, default=''
        )
        # self.arg_parser.add_argument(
        # '--onlyselection', action="store", type=str,
        # choices=['true', 'false'], default='true'
        # )
        self.arg_parser.add_argument(
            '--optimize', action="store", type=str,
            choices=['true', 'false'], default='false'
        )
        self.arg_parser.add_argument(
            '--report', action="store", type=str,
            choices=['true', 'false'], default='false'
        )
        self.arg_parser.add_argument(
            '--preview', action="store", type=str,
            choices=['true', 'false'], default='false'
        )

    def generate_bmp(self, tmp_bmp):
        with tmp_file(".png", text=False) as tmp_png:
            with self.as_tmp_svg() as tmp_svg:
                if(self.onlyselected()):
                    inkscape_command(tmp_svg, '-z', '-D', '-b', '#ffffff', '-y', '1', '-d', self.options.resolution, '-e', tmp_png)
                else:
                    inkscape_command(tmp_svg, '-z', '-C', '-b', '#ffffff', '-y', '1', '-d', self.options.resolution, '-e', tmp_png)

                if(self.options.processmode in ['Layer', 'Relief']):
                    # convert_command(tmp_png, '-flip', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'h8x8a,256', '-depth', '8', '-alpha', 'off', '-compress', 'NONE', '-colors', '256', 'BMP3:%s' % tmp_bmp)
                    # convert_command(tmp_png, '-flip', '-level', '0%,100%,4.0', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'o8x8,16', '-depth', '8', '-alpha', 'off', '-compress', 'NONE', '-colors', '256', 'BMP3:%s' % tmp_bmp)
                    convert_command(tmp_png, '-flip', '-level', '0%,100%,4.0', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'o8x8,16', '-depth', '8', '-alpha', 'off', '-remap', os.path.join(os.getcwd(), 'fablab_grayscale.bmp'), '-compress', 'NONE', 'BMP3:%s' % tmp_bmp)

                else:
                    # convert_command(tmp_png, '-flip', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'h8x8a,256', '-depth', '8', '-alpha', 'off', '-compress', 'NONE', '-colors', '256', 'BMP3:%s' % tmp_bmp)
                    # convert_command(tmp_png, '-flip', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'h4x4a', '-monochrome', '-depth', '1', '-alpha', 'off', '-compress', 'NONE', '-colors', '2', 'BMP3:%s' % tmp_bmp)
                    convert_command(tmp_png, '-flip', '-level', '0%,100%,4.0', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'o8x8', '-remap',
                                    os.path.join(os.getcwd(), 'fablab_monochrome.bmp'), '-compress', 'NONE', 'BMP3:%s' % tmp_bmp)

    def onlyselected(self):
        return self.svg.selected #and self.options.onlyselection == 'true'

    def job_filepath(self):
        filepath = os.path.join(self.options.spoolpath, "%s.tsf" % (self.options.jobname))
        jobname = self.options.jobname
        cnt = 1
        while(os.path.isfile(filepath)):
            cnt += 1
            jobname = "%s_%s" % (self.options.jobname, cnt)
            filepath = os.path.join(self.options.spoolpath, "%s_%s.tsf" % (self.options.jobname, cnt))

        return jobname, filepath

    def paths_to_unit_segments(self, path_nodes):
        if self.options.optimize == 'false':
            for path in path_nodes:
                for points in path_to_segments(path):
                    yield points
        else:
            # optimise
            # for polyline in Polyline.generate_from_segments(Segment.convertToSegmentSet(path_nodes)):
            fablab_path_lib.update_precision_factor(self.svg.unittouu("10px"))
            for polyline in Polyline.generate_from_segment_array(list(Segment.convertToSegmentSet(path_nodes))):
                for points in pathd_to_segments(polyline.format()):
                    yield points

    def effect(self):
        self.options.processmode = self.options.processmode.replace('"', '')

        start_time = time.time()
        ink_args = []

        if(self.options.spoolpath):
            if not os.path.isdir(self.options.spoolpath):
                inkex.errormsg(u"Le chemin spécifié (%s) pour le répértoire de spool où seront exportés les fichier tsf est incorrect." % self.options.spoolpath)
                return

        tmp_f = '/tmp/obj-to-path.svg'

       
        actions = '--actions=select-all;object-to-path;export-filename:%s;export-do;' % tmp_f
        inkex.command.inkscape(actions, self.options.input_file)
        inkex.errormsg("inkscape %s %s" % (actions, self.options.input_file))
        with open(tmp_f) as tmp:
            doc = inkex.load_svg(tmp)
            root = doc.getroot()

            inkex.errormsg('== nb text : %s' % len(list(root.iterdescendants("{http://www.w3.org/2000/svg}text"))))
            # get document size to test if path are in visble zone
            print_("get document size to test if path are in visble zone %s" % tmp)
            doc_width, doc_height = self.svg.unittouu(root.get('width')), self.svg.unittouu(root.get('height'))
            output_file = None

            # start generating tsf
            print_("start generating tsf")
            filepath = None
            if self.options.spoolpath:
                jobanme, filepath = self.job_filepath()
                output_file = open(filepath, "w")
                self.initialize_tsf(self.options, doc_width, doc_height, jobname=jobanme, output=output_file)
            else:
                self.initialize_tsf(self.options, doc_width, doc_height)

            self.write_tsf_header()

            # get paths to cut from file, store them by color
            print_("get paths to cut from file, store them by color")
            paths_by_color = {}
            for path in root.iterdescendants("{http://www.w3.org/2000/svg}path"):
                path_style = dict(inkex.Style.parse_str(path.get('style', '')))
                path_color = path_style.get('stroke', None)
                inkex.errormsg('== path : %s' % path)
                inkex.errormsg('== color : %s' % path_color)
                inkex.errormsg('==doc size : %sx%s' %(doc_width,doc_height))
                if path_color in TROTEC_COLORS:
                    try:
                        bbox = path.bounding_box()
                        if self.onlyselected() or all([
                            bbox.left >= 0, 
                            bbox.top >= 0, 
                            bbox.right <= doc_width, 
                            bbox.bottom <= doc_height
                        ]):
                            inkex.errormsg("Path is ok")
                            path_style['stroke-opacity'] = '0'
                            path.set('style', str(inkex.Style(path_style)))
                            paths_by_color.setdefault(path_color, []).append(path)
                    except TypeError:
                        inkex.errormsg("TypeError ops !")
                        pass

            inkex.errormsg("== paths_by_color : %s" % paths_by_color)

            with tmp_file(".bmp", text=False) as tmp_bmp:
                try:
                    # generate png then bmp for engraving
                    print_("generate png then bmp for engraving")
                    if(self.options.processmode != 'None'):
                        self.generate_bmp(tmp_bmp)
                        if(identify_command('-format', '%k', tmp_bmp).strip() != "1"):  # If more than one color in png output
                            self.write_tsf_picture(tmp_bmp)
                except ImageMagickError:
                    inkex.errormsg(u"⚠️ Impossible de générer le fichier de gravure. \n\nImageMagick est il correctement installé ?\n")

                # adding polygones
                print_("generate png then bmp for engraving")
                with self.draw_tsf_commands() as draw_polygon:
                    for path_color in paths_by_color:
                        r, g, b = inkex.Color(path_color).to_rgb()
                        for points in self.paths_to_unit_segments(
                            paths_by_color[path_color]
                        ):
                            draw_polygon(r, g, b, points)

                end_time = time.time()

            if output_file:
                try:
                    output_file.close()
                except OSError:
                    pass
            else:
                inkex.errormsg(u"\n Cliquer sur valider pour terminer l'enregistrement du fichier.")

            # Display preview
            if self.options.preview == 'true':
                if(filepath):
                    print_("filepath : %s" % filepath)
                    try:
                        TsfFilePreviewer(filepath, export_time=round(end_time - start_time, 1)).show_preview()
                    except Exception as e:
                        inkex.errormsg(u"Votre fichier est prêt à être decoupé.")
                        # raise(e)
                else:
                    pass
            else:
                inkex.errormsg(u"Votre fichier est prêt à être decoupé.")

if __name__ == '__main__':
    TsfEffect().run(output=False)
