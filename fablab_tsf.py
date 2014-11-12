import sys
import os


class DrawPolygon:
    def __init__(self, r, g, b, points=[]):
        self.colors = (r, g, b)
        self.points = points

    def output(self):
        o = [len(self.points)]
        o.extend(self.colors)
        for pt in self.points:
            o.extend(pt)
        print('<DrawPolygon: %s>' % ";".join((str(i) for i in o)))

    def add_point(self, x, y):
        self.points.append([x, y])


class TsfFile:
    def __init__(self):
        self.header = {
            'ProcessMode': 'Standard',
            'Size': (10.0, 10.0),
            'MaterialGroup': 'Standard',
            'MaterialName': 'Standard',
            'JobName': 'job',
            'JobNumber': 1,
            'Resolution': 500,
            'Cutline': 'none',
            'LayerParameters': (2, 0.0),
            'StampShoulder': 'flat'
        }
        self.image = None
        self.draw_commands = []

    def simple_header_out(self, name, default):
        print('<%s: %s>' % (name, self.header.get(name, default)))

    def output(self):
        print('<!-- Version: 9.4.2.1034>')
        print('<!-- PrintingApplication: inkscape.exe>')

        print('<BegGroup: Header>')
        self.simple_header_out('ProcessMode', 'Standard')
        print('<Size: %s;%s>' % self.header.get('Size', (0.0, 0.0)))

        if self.header.get('ProcessMode', 'Standard') == 'Layer':
            print("<LayerParameter: %s;%s>" % self.get('LayerParameters', (2, 0.0)))

        if self.header.get('ProcessMode', 'Standard') == 'Stamp':
            print("<StampShoulder: %s>" % self.get('StampShoulder', 'flat'))

        self.simple_header_out('MaterialGroup', 'Standard')
        self.simple_header_out('MaterialName', 'Standard')
        self.simple_header_out('JobName', 'bbb_sq10')
        self.simple_header_out('JobNumber', '2')
        self.simple_header_out('Resolution', '500')
        self.simple_header_out('Cutline', 'none')
        print('<EndGroup: Header>')

        if self.image is not None and os.path.isfile(self.image):
            print('<BegGroup: Bitmap>')
            sys.stdout.write('<STBmp: 0;0>')
            with open(self.image, 'rb') as image:
                sys.stdout.write(image.read())
            sys.stdout.write('<EOBmp>')
            print('<EndGroup: Bitmap>')

        if self.draw_commands:
            print('<BegGroup: DrawCommands>')
            for draw_command in self.draw_commands:
                draw_command.output()
            print('<EndGroup: DrawCommands>')

    def add_polygon(self, polygon):
        self.draw_commands.append(polygon)

if __name__ == '__main__':
    tsf = TsfFile()
    poly = DrawPolygon(255, 0, 0, [[0, 0], [196/2, 0], [196/2, 196/2], [196,196/2], [196, 196]])
    tsf.add_polygon(poly)
    tsf.output()