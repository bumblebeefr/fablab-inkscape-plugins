#!/usr/bin/env python
from os import path
import sys
sys.path.append('/usr/share/inkscape/extensions')


def print_(*arg):
    f = open("fablab_debug.log", "a")
    for s in arg:
        s = str(unicode(s).encode('unicode_escape')) + " "
        f.write(s)
    f.write("\n")
    f.close()


HEADER = ''';GCode file for proxxon CNC lathe and nncad
;Generated with Inkscape gcodetool plugin
;
G90
M10 O6.1

'''


FOOTER = '''
M10 O6.0
'''


def main():
    for a in sys.argv:
        if(a.startswith("--directory=")):
            directory = a[len("--directory="):]
            header_file = path.join(directory, "header")
            footer_file = path.join(directory, "footer")

            if not path.isfile(header_file):
                with open(header_file, 'w') as f:
                    f.write(HEADER)

            if not path.isfile(footer_file):
                with open(footer_file, 'w') as f:
                    f.write(FOOTER)

            with open("/tmp/inkscape.log", "a") as f:
                f.write("Directory argument  : %s \n" % directory)

    import gcodetools

if __name__ == '__main__':
    main()
