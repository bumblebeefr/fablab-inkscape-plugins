#!/usr/bin/env python
# encoding: utf-8
import os
import simplestyle
import time

from fablab_lib import *
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
        self.OptionParser.add_option('--report', action="store", type='choice', choices=['true', 'false'], default='false')
        self.OptionParser.add_option('--preview', action="store", type='choice', choices=['true', 'false'], default='false')

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
        return self.selected and self.options.onlyselection == 'true'

    def job_filepath(self):
        filepath = os.path.join(self.options.spoolpath, "%s.tsf" % (self.options.jobname))
        jobname = self.options.jobname
        cnt = 0
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
            fablab_path_lib.update_precision_factor(self.unittouu("10px"))
            for polyline in Polyline.generate_from_segment_array(list(Segment.convertToSegmentSet(path_nodes))):
                for points in pathd_to_segments(polyline.format()):
                    yield points

    def effect(self):
        start_time = time.time()
        ink_args = []

        if(self.options.spoolpath):
            if not os.path.isdir(self.options.spoolpath):
                inkex.errormsg(u"Le chemin spécifié (%s) pour le répértoire de spool où seront exportés les fichier tsf est incorrect." % self.options.spoolpath)
                return

        # unlock all object to be able do to what we want on it
        ink_args.append("--verb=LayerUnlockAll")
        ink_args.append("--verb=UnlockAllInAllLayers")

        # remove all objects not in selection
        if(self.onlyselected()):
            for k in self.selected:
                ink_args.append('--select=%s' % k)

            ink_args.append("--verb=EditInvertInAllLayers")
            ink_args.append("--verb=EditDelete")
            ink_args.append("--verb=FitCanvasToDrawing")

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

        with self.inkscaped(ink_args, needX=True) as tmp:
            # get document size to test if path are in visble zone
            print_("get document size to test if path are in visble zone %s" % tmp)
            doc_width, doc_height = self.unittouu(self.document.getroot().get('width')), self.unittouu(self.document.getroot().get('height'))
            output_file = None

            # start generating tsf
            print_("start generating tsf")
            filepath = None
            if self.options.spoolpath:
                jobanme, filepath = self.job_filepath()
                output_file = open(filepath, "wb")
                self.initialize_tsf(self.options, doc_width, doc_height, jobname=jobanme, output=output_file)
            else:
                self.initialize_tsf(self.options, doc_width, doc_height)

            self.write_tsf_header()

            # get paths to cut from file, store them by color
            print_("get paths to cut from file, store them by color")
            paths_by_color = {}
            for path in self.document.getroot().iterdescendants("{http://www.w3.org/2000/svg}path"):
                path_style = simplestyle.parseStyle(path.get('style', ''))
                path_color = path_style.get('stroke', None)
                if path_color in TROTEC_COLORS:
                    try:
                        xmin, xmax, ymin, ymax = simpletransform.computeBBox([path])
                        if self.onlyselected() or all([xmin >= 0, ymin >= 0, xmax <= doc_width, ymax <= doc_height]):
                            path_style['stroke-opacity'] = '0'
                            path.set('style', simplestyle.formatStyle(path_style))
                            paths_by_color.setdefault(path_color, []).append(path)
                    except TypeError:
                        pass

            with tmp_file(".bmp", text=False) as tmp_bmp:
                # generate png then bmp for engraving
                print_("generate png then bmp for engraving")
                if(self.options.processmode != 'None'):
                    self.generate_bmp(tmp_bmp)
                    if(identify_command('-format', '%k', tmp_bmp).strip() != "1"):  # If more than one color in png output
                        self.write_tsf_picture(tmp_bmp)

                # adding polygones
                print_("generate png then bmp for engraving")
                with self.draw_tsf_commands() as draw_polygon:
                    for path_color in paths_by_color:
                        r, g, b = simplestyle.parseColor(path_color)
                        for points in self.paths_to_unit_segments(paths_by_color[path_color]):
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
    TsfEffect().affect(output=False)
