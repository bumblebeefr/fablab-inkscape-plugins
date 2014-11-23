#!/usr/bin/env python
# encoding: utf-8
from contextlib import contextmanager
import os
import platform
import sys
import tempfile
import simplestyle

from fablab_lib import *
from fablab_tsf_lib import TsfFile

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
                    convert_command(tmp_png, '-flip', '-fx', '(r+g+b)/3', '-colorspace', 'Gray', '-ordered-dither', 'h8x8a,256', '-depth', '8', '-alpha', 'off', '-compress', 'NONE', '-colors', '256', 'BMP3:%s' % tmp_bmp)
                else:
                    convert_command(tmp_png, '-flip', '-fx', '(r+g+b)/3', '-colorspace', 'Gray', '-ordered-dither', 'h4x4a', '-monochrome', tmp_bmp)

    def onlyselected(self):
        return self.selected and self.options.onlyselection == 'true'

    def effect(self):
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
                filepath = os.path.join(self.options.spoolpath, self.options.jobname + ".tsf")
                output_file = open(filepath, "w")
                tsf = TsfFile(self.options, doc_width, doc_height, doc_offset_x, doc_offset_y, output=output_file)
            else:
                tsf = TsfFile(self.options, doc_width, doc_height, doc_offset_x, doc_offset_y)

            tsf.write_header()


            # adding polygones
            with tsf.draw_commands() as draw_polygon:
                for path in self.document.getroot().iterdescendants("{http://www.w3.org/2000/svg}path"):
                    path_style = simplestyle.parseStyle(path.get('style', ''))
                    path_color = path_style.get('stroke', None)
                    if path_color in TROTEC_COLORS:
                        xmin, xmax, ymin, ymax = simpletransform.computeBBox([path])
                        if all([xmin >= 0, ymin >= 0, xmax <= doc_width, ymax <= doc_height]):
                            r, g, b = simplestyle.parseColor(path_color)
                            for points in path_to_segments(path):
                                draw_polygon(r, g, b, points)
                        path_style['stroke'] = 'none'
                        path.set('style', simplestyle.formatStyle(path_style))

            # generate png then bmp for engraving
            if(self.options.processmode != 'None'):
                with tmp_file(".bmp", text=False) as tmp_bmp:
                    self.generate_bmp(tmp_bmp)
                    tsf.write_picture(tmp_bmp)

            if output_file:
                try:
                    output_file.close()
                except OSError:
                    pass
                finally:
                    inkex.errormsg(u" ☯ Génération du fichier TSF effectuée.")
            else:
                inkex.errormsg(u" ☯ Génération du fichier TSF effectuée, cliquer sur valider pour terminer l'enregistrement du fichier.")

if __name__ == '__main__':
    TsfEffect().affect(output=False)
