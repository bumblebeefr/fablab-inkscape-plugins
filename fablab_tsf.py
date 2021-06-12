#!/usr/bin/env python
# encoding: utf-8
import os
from lxml import etree
import inkex.command
from inkex.extensions import EffectExtension
from inkex.transforms import BoundingBox
from inkex.units import parse_unit
import time
import tempfile
from itertools import chain
from contextlib import contextmanager


from fablab_lib import (
    ImageMagickError, execute_command, execute_async_command, inkscape_command,
    inkscapeX_command, convert_command, identify_command, hex_color,
    tmp_file, print_, path_to_segments, pathd_to_segments, subdivideCubicPath
)
from fablab_tsf_lib import TsfFileEffectMixin
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


def iter_path_nodes(element):
    inkex.errormsg("== element.tag : %s" % element.tag)
    if element.tag == '{http://www.w3.org/2000/svg}path':
        yield element
    else:
        yield from element.iterdescendants(
            "{http://www.w3.org/2000/svg}path"
        )


class TsfEffect(EffectExtension, TsfFileEffectMixin):

    def add_arguments(self, pars):
        pars.add_argument(
            '--tabs', action='store', type=str, default='Job')
        pars.add_argument(
            '--processmode', action='store', type=str, choices=[
                'None', 'Standard', 'Layer', 'Stamp', 'Relief'
            ], default='None'
        )
        pars.add_argument(
            '--jobname', action='store', type=str, default='Job'
        )
        pars.add_argument(
            '--jobnumber', action='store', type=int, default=1
        )
        pars.add_argument(
            '--resolution', action='store', type=int, default=500
        )
        pars.add_argument(
            '--layernumber', action='store', type=int, default=1
        )
        pars.add_argument(
            '--layeradjustement', action='store', type=float, default=0
        )
        pars.add_argument(
            '--stampshoulder', action='store', type=str,
            choices=['flat', 'medium', 'steep'], default='flat'
        )
        pars.add_argument(
            '--cutline', action='store', type=str,
            choices=['none', 'circular', 'rectangular', 'optimized'],
            default='none'
        )
        pars.add_argument(
            '--spoolpath', action='store', type=str, default=''
        )
        pars.add_argument(
            '--report', action="store", type=str,
            choices=['true', 'false'], default='false'
        )
        pars.add_argument(
            '--preview', action="store", type=str,
            choices=['true', 'false'], default='false'
        )
        pars.add_argument(
            '--optimize', action="store", type=str,
            choices=['true', 'false'], default='false'
        )

    @contextmanager
    def as_tmp_svg(self):
        '''
            Work on a temporary .svg copy of this document.
            example :

            with self.as_tmp_svg as temp_svg:
                print tmp
        '''
        fd, tmp = tempfile.mkstemp(".svg", text=True)
        os.close(fd)
        self.document.write(tmp)
        try:
            yield tmp
        finally:
            try:
                pass
                # os.remove(tmp)
            except(OSError):
                pass

    def generate_bmp(self, tmp_bmp):
        with tmp_file(".png", text=False) as tmp_png:
            with self.as_tmp_svg() as tmp_svg:
                if(self.onlyselected()):
                    inkscape_command(tmp_svg, '-z', '-D', '-b', '#ffffff',
                                     '-y', '1', '-d', self.options.resolution, '-e', tmp_png)
                else:
                    inkscape_command(tmp_svg, '-z', '-C', '-b', '#ffffff',
                                     '-y', '1', '-d', self.options.resolution, '-e', tmp_png)

                if(self.options.processmode in ['Layer', 'Relief']):
                    # convert_command(tmp_png, '-flip', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'h8x8a,256', '-depth', '8', '-alpha', 'off', '-compress', 'NONE', '-colors', '256', 'BMP3:%s' % tmp_bmp)
                    # convert_command(tmp_png, '-flip', '-level', '0%,100%,4.0', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'o8x8,16', '-depth', '8', '-alpha', 'off', '-compress', 'NONE', '-colors', '256', 'BMP3:%s' % tmp_bmp)
                    convert_command(tmp_png, '-flip', '-level', '0%,100%,4.0', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'o8x8,16',
                                    '-depth', '8', '-alpha', 'off', '-remap', os.path.join(os.getcwd(), 'fablab_grayscale.bmp'), '-compress', 'NONE', 'BMP3:%s' % tmp_bmp)

                else:
                    # convert_command(tmp_png, '-flip', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'h8x8a,256', '-depth', '8', '-alpha', 'off', '-compress', 'NONE', '-colors', '256', 'BMP3:%s' % tmp_bmp)
                    # convert_command(tmp_png, '-flip', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'h4x4a', '-monochrome', '-depth', '1', '-alpha', 'off', '-compress', 'NONE', '-colors', '2', 'BMP3:%s' % tmp_bmp)
                    convert_command(tmp_png, '-flip', '-level', '0%,100%,4.0', '-separate', '-average', '-colorspace', 'Gray', '-ordered-dither', 'o8x8', '-remap',
                                    os.path.join(os.getcwd(), 'fablab_monochrome.bmp'), '-compress', 'NONE', 'BMP3:%s' % tmp_bmp)

    def onlyselected(self):
        return True if self.svg.selected else False

    def job_filepath(self):
        filepath = os.path.join(self.options.spoolpath,
                                "%s.tsf" % (self.options.jobname))
        jobname = self.options.jobname
        cnt = 1
        while(os.path.isfile(filepath)):
            cnt += 1
            jobname = "%s_%s" % (self.options.jobname, cnt)
            filepath = os.path.join(
                self.options.spoolpath,
                "%s_%s.tsf" % (self.options.jobname, cnt)
            )

        return jobname, filepath

    def paths_to_unit_segments(self, path_nodes):
        for path in path_nodes:
            for points in path_to_segments(path):
                yield points

    def has_changed(self, ret):
        # we do not want modifications to be visible after plugin execution
        return False

    def is_in_viewbox(self, bbox):
        viewbox = self.svg.get_viewbox()
        return all([
            bbox.left >= viewbox[0],
            bbox.top >= viewbox[1],
            bbox.right <= viewbox[0]+viewbox[2],
            bbox.bottom <= viewbox[1]+viewbox[3]
        ])

    def fully_transformed_bounding_box(self, element):
        transform_chain = element.composed_transform()
        ftbbox = element.bounding_box(transform_chain)

        inkex.errormsg('Node to compute bbox for : %s #%s' %
                       (element.tag, element.get('id')))
        inkex.errormsg(' -> transform_chain: %s' % transform_chain)
        inkex.errormsg(' -> simple bbox : %s' % element.bounding_box())
        inkex.errormsg(' -> full tranformed bbox : %s' % ftbbox)

        return ftbbox

    def iter_descendents(self, element):
        yield element
        yield from element.iterdescendants()

    def iter_selected_descendents(self):
        """iterator on selected "leaf" nodes insides selecd groups if needed
           should not yield group elements"""
        return filter(
            lambda element: element.tag != "{http://www.w3.org/2000/svg}g",
            chain(*[
                self.iter_descendents(element)
                for element in self.svg.selected.values()
            ])
        )

    def get_selected_bbox(self):
        """Gets the bounding box of the selected items"""
        bboxes = (
            self.fully_transformed_bounding_box(node)
            for node
            in self.iter_selected_descendents()
        )
        return sum(bboxes, start=BoundingBox(None))

    @property
    def unit(self):
        return parse_unit(self.svg.get('width'))[1]

    def effect(self):
        self.options.processmode = self.options.processmode.replace('"', '')

        start_time = time.time()
        ink_args = []

        if(self.options.spoolpath):
            if not os.path.isdir(self.options.spoolpath):
                inkex.errormsg(
                    u"Le chemin spécifié (%s) pour le répértoire de spool où seront exportés les fichier tsf est incorrect." % self.options.spoolpath)
                return

        working_file = self.options.input_file

        # update viewbox to match selection
        if(self.onlyselected()):
            selection_bbox = self.get_selected_bbox()
            inkex.errormsg('Selection bbox0 : %s' %
                           self.svg.get_selected_bbox())
            inkex.errormsg('Selection bbox : %s' % selection_bbox)
            self.svg.set(
                'viewBox', f'{selection_bbox.left} {selection_bbox.top} {selection_bbox.width} {selection_bbox.height}')
            self.svg.set('width', f'{selection_bbox.width}{self.unit}')
            self.svg.set('height', f'{selection_bbox.height}{self.unit}')
            document = etree.tostring(self.document)
            with open('/tmp/output.svg', 'w+') as f:
                f.write(document.decode('utf-8'))
            del document
            working_file = '/tmp/output.svg'

        inkex.errormsg("View box %s" % self.svg.get_viewbox())

        tmp_f = '/tmp/tmp.svg'
        actions = '--actions=select-all;object-unlink-clones;select-all;object-to-path;export-filename:%s;export-do;' % tmp_f
        inkex.command.inkscape(actions, working_file)
        with open(tmp_f) as tmp:
            doc = inkex.load_svg(tmp)
            root = doc.getroot()
            root.set_selected(*self.options.ids)

            # get document size to test if path are in visble zone
            print_("get document size to test if path are in visble zone %s" % tmp)
            doc_width = self.svg.unittouu(root.get('width'))
            doc_height = self.svg.unittouu(root.get('height'))
            output_file = None

            # start generating tsf
            print_("start generating tsf")
            jobanme, filepath = self.job_filepath()
            output_file = open(filepath, "w")
            viewbox = self.svg.get_viewbox()
            self.initialize_tsf(
                options=self.options,
                w=doc_width,
                h=doc_height,
                jobname=jobanme,
                output=output_file,
                offset_x=viewbox[0],
                offset_y=viewbox[1]
            )

            self.write_tsf_header()

            # get paths to cut from file, store them by color
            print_("get paths to cut from file, store them by color")
            paths_by_color = {}

            if self.onlyselected():
                selection_bbox = root.get_selected_bbox()
                inkex.errormsg("selection bbox %s" % selection_bbox)
                iterdescendants = [
                    iter_path_nodes(node)
                    for node in root.selected.values()
                ]
                path_itertor = chain(*iterdescendants)
            else:
                path_itertor = iter_path_nodes(root)

            inkex.errormsg('==doc size : %sx%s' % (doc_width, doc_height))
            for path_element in path_itertor:
                path_style = dict(inkex.Style.parse_str(
                    path_element.get('style', '')))
                path_color = path_style.get('stroke', None)
                inkex.errormsg('== path_element : %s #%s' %
                               (path_element, path_element.get('id')))
                inkex.errormsg('  -> style : %s' % (path_style))
                if path_color in TROTEC_COLORS:
                    # make path not visible
                    path_style['stroke-opacity'] = '0'
                    path_style['stroke-width'] = '0'
                    path_element.set('style', str(inkex.Style(path_style)))
                    try:
                        bbox = self.fully_transformed_bounding_box(
                            path_element
                        )
                        inkex.errormsg(' -> path_element bbox : %s' % bbox)
                        if self.onlyselected() or self.is_in_viewbox(bbox):
                            inkex.errormsg("    -> Path is ok to use")
                            inkex.errormsg(
                                ' -> path_element type : %s' % type(path_element))

                            paths_by_color.setdefault(
                                path_color, []
                            ).append(
                                path_element
                            )
                    except TypeError as e:
                        inkex.errormsg("TypeError oops : %s" % e)
                        pass

            inkex.errormsg("== paths_by_color : %s" % paths_by_color)

            with tmp_file(".bmp", text=False) as tmp_bmp:
                try:
                    # generate png then bmp for engraving
                    print_("generate png then bmp for engraving")
                    if(self.options.processmode != 'None'):
                        self.generate_bmp(tmp_bmp)
                        # If more than one color in png output
                        if(identify_command('-format', '%k', tmp_bmp).strip() != "1"):
                            self.write_tsf_picture(tmp_bmp)
                except ImageMagickError:
                    inkex.errormsg(
                        u"⚠️ Impossible de générer le fichier de gravure. \n\nImageMagick est il correctement installé ?\n")

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
                inkex.errormsg(
                    "\n Cliquer sur valider pour terminer ",
                    "l'enregistrement du fichier."
                )

            # Display preview
            if self.options.preview == 'true':
                if(filepath):
                    print_("filepath : %s" % filepath)
                    try:
                        TsfFilePreviewer(
                            filepath,
                            export_time=round(
                                end_time - start_time, 1
                            )
                        ).show_preview()
                    except Exception as e:
                        inkex.errormsg(
                            u"Votre fichier est prêt à être decoupé."
                        )
                else:
                    pass
            else:
                inkex.errormsg(u"Votre fichier est prêt à être decoupé.")


if __name__ == '__main__':
    TsfEffect().run(output=False)
