import re
import logging
import os
import tempfile
from fablab_lib import convert_command
import base64
from os import path
import hashlib
from datetime import datetime
import errno
import webbrowser

headers_re = {
    'ProcessMode': re.compile('<ProcessMode: (.*)>'),
    'Size': re.compile('<Size: ([0-9\.]*);([0-9\.]*)>'),
    'MaterialGroup': re.compile('<MaterialGroup: (.*)>'),
    'MaterialName': re.compile('<MaterialName: (.*)>'),
    'JobName': re.compile('<JobName: (.*)>'),
    'JobNumber': re.compile('<JobNumber: ([0-9]*)>'),
    'Resolution': re.compile('<Resolution: ([0-9]*)>'),
    'LayerParameter': re.compile('<LayerParameter: ([0-9]*);([0-9\.]*)>'),
    'StampShoulder': re.compile('<StampShoulder: (.*)>'),
    'Cutline': re.compile('<Cutline: (.*)>'),
}
headers_transfo = {
    'ProcessMode': lambda x: x[0],
    'Size': lambda x: {'width': float(x[0]), 'height': float(x[1])},
    'MaterialGroup': lambda x: x[0].decode('iso-8859-1'),
    'MaterialName': lambda x: x[0].decode('iso-8859-1'),
    'JobName': lambda x: x[0].decode('iso-8859-1'),
    'JobNumber': lambda x: int(x[0]),
    'Resolution': lambda x: int(x[0]),
    'LayerParameter': lambda x: {'layers': int(x[0]), 'adjustment': float(x[1])},
    'StampShoulder': lambda x: x[0],
    'Cutline': lambda x: x[0],
}


bmp_re = re.compile('<STBmp: (.*)>BM(.*)<EOBmp>', re.S)
polygones_re = re.compile('<DrawPolygon: ([0-9;]*)>')

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


def group(t, n):
    return zip(*[t[i::n] for i in range(n)])


def mm2px(dpi, val):
    return int(round(1.0 * val * dpi * 0.0393701))


def hex_color(rgb_tuple):
    hexcolor = '#%02x%02x%02x' % tuple([int(x) for x in rgb_tuple])
    return hexcolor


def polygon_topath(data):
    polygons = data[4:]
    color = data[1:4]
    path = ['<path style="stroke:%s; fill:none; stroke-width: 3;" ' % hex_color(color), 'd="M']
    for p in group(polygons, 2):
        path.append("%s,%s " % tuple(p))
    path.append('" />')
    return "".join(path)


def get_base64_img(tsf_buff):
    encoded_string = None
    m = bmp_re.search(tsf_buff)
    if m:
        _bmp_file, _bmp_filename = tempfile.mkstemp(suffix=".bmp")
        os.write(_bmp_file, "BM")
        os.write(_bmp_file, m.group(2))
        os.close(_bmp_file)
        _jpg_file, _jpg_filename = tempfile.mkstemp(suffix=".jpg")
        os.close(_jpg_file)
        # convert_command(_bmp_filename, "-resize", '"1920x1080>"', "-flip", _jpg_filename)
        convert_command(_bmp_filename, "-flip", _jpg_filename)
        with open(_jpg_filename, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
        os.remove(_bmp_filename)
        os.remove(_jpg_filename)
        return encoded_string


def parse_headers(tsf_file):
    try:
        with open(tsf_file, "r") as f:
            tsf_buff = f.read()

            headers = {}
            for k in headers_re:
                if(headers_re[k].search(tsf_buff)):
                    headers[k] = headers_transfo[k](headers_re[k].search(tsf_buff).groups())

            headers['px_width'] = mm2px(headers['Resolution'], headers['Size']['width'])
            headers['px_height'] = mm2px(headers['Resolution'], headers['Size']['height'])
            headers['bmp'] = False

            if(bmp_re.search(tsf_buff)):
                headers['bmp'] = True

            colors = set()
            for p in polygones_re.findall(tsf_buff):
                colors.add(hex_color(p.split(';')[1:4]))

            headers['cut'] = list(colors)

            headers['valid'] = True
            return headers
    except Exception:
        logging.exception("Error loading headers for %s" % tsf_file)
        return {"valid": False}


def parse_headers2(tsf_file):
    try:
        with open(tsf_file, "r") as _file:
            headers = {
                'ProcessMode': None,
                'Size': {'width': 0, 'height': 0},
                'MaterialGroup': None,
                'MaterialName': None,
                'JobName': None,
                'JobNumber': 0,
                'Resolution': 300,
                'LayerParameter': {'layers': 1, 'adjustment': 0},
                'StampShoulder': None,
                'Cutline': [],
            }
            headers['bmp'] = False
            colors = set()
            for line in _file:
                for k in headers_re:
                    found = headers_re[k].search(line)
                    if(found):
                        headers[k] = headers_transfo[k](found.groups())
                        break

                if line.find('<BegGroup: Bitmap>') > -1:
                    headers['bmp'] = True

                for p in polygones_re.findall(line):
                    colors.add(hex_color(p.split(';')[1:4]))

            headers['px_width'] = mm2px(headers['Resolution'], headers['Size']['width'])
            headers['px_height'] = mm2px(headers['Resolution'], headers['Size']['height'])
            headers['valid'] = True

            headers['cut'] = [k for k in TROTEC_COLORS if k in colors]
            return headers
    except Exception:
        logging.exception("Error loading headers for %s" % tsf_file)
        return {"valid": False}

# deprecated won't work anymore


def extract_preview(tsf_file, headers, svg_path):
    engrave_img = None
    try:
        with open(tsf_file, "r") as f:
            tsf_buff = f.read()
            engrave_img = get_base64_img(tsf_buff)

    except Exception:
        logging.exception("Error extracting preview for %s" % tsf_file)

    with open(svg_path, "w+") as svg_file:
        svg_file.write(extract_svg(tsf_file, headers, engrave_img))


def extract_svg(tsf_file, headers, engrave_img=None):
    with open(tsf_file, "r") as f:
        tsf_buff = f.read()
        svg = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 %s %s" >' % (headers.get("px_width"), headers.get("px_height"))]
        if(engrave_img):
            # with open(jpg_path, "rb") as img:
                # svg.append('<image x="0" y="0" width="%s" height="%s" xlink:href="data:image/jpg;base64,%s" />' % (headers.get("px_width"), headers.get("px_height"), img.read().encode("base64").replace('\n', '')))
            svg.append('<image x="0" y="0" width="%s" height="%s" xlink:href="data:image/jpg;base64,%s" />' % (headers.get("px_width"), headers.get("px_height"), engrave_img))
        for p in polygones_re.findall(tsf_buff):
            svg.append(polygon_topath(p.split(';')))
        svg.append("</svg>")
    return "\n".join(svg)


def mkdir(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def str_weight(weight):
    i = 0
    while weight > 1024:
        weight = 1.0 * weight / 1024
        i += 1
    # logging.debug(weight)
    return "%0.1f%s" % (weight, ("o", "Ko", "Mo", "Go", "To")[i])


class TsfFilePreviewer:

    def __init__(self, full_path):
        if not path.isfile(full_path):
            raise Exception("%s is not a file" % full_path)

        self.full_path = full_path
        self.directory, self.filename = path.split(self.full_path)
        self.name = self.filename.replace(".tsf", "")
        self._checksum = None
        self._headers = None
        self.creation_date = datetime.fromtimestamp(path.getctime(full_path))
        self.modification_date = datetime.fromtimestamp(path.getmtime(full_path))
        self.size = path.getsize(full_path)

    def checksum_md5(self):
        if not self._checksum:
            md5 = hashlib.md5()
            with open(self.full_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    md5.update(chunk)
            self._checksum = md5.hexdigest()
        return self._checksum

    def to_dict(self):
        return {
            'directory': self.directory,
            'filename': self.filename,
            'checksum': self.checksum_md5(),
            'headers': self.headers(),
            'date': self.creation_date.isoformat(),
            'weight': self.size,
            'sweight': str_weight(self.size)
        }

    def headers(self):
        if self._headers is None:
            self._headers = parse_headers2(self.full_path)
        return self._headers

    def generate_preview(self, preview_svg):
        extract_preview(self.full_path, self.headers(), preview_svg)
        return preview_svg

    def show_preview(self):
        _preview_file, _preview = tempfile.mkstemp(".svg")
        os.close(_preview_file)
        self.generate_preview(_preview)
        try:
            webbrowser.get('firefox').open(_preview)
        except:
            try:
                webbrowser.get('chrome').open(_preview)
            except:
                webbrowser.open(_preview, new=1)
#        os.remove(_preview)
