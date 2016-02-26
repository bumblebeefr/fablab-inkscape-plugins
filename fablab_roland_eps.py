#!/usr/bin/env python
import sys,os
import inkex
from math import *
import getopt
import shutil


def print_(*arg):
    f = open("fablab_debug.log","a")
    for s in arg :
        s = str(unicode(s).encode('unicode_escape'))+" "
        f.write( s )
    f.write("\n")
    f.close()


if __name__ == '__main__':

    with open(sys.argv[-1]) as f:
        endcomments = False
        for line in f:
            if(line.startswith("%%EndComments")):
                print("%%DocumentCustomColors: (CutContour)")
                print("%%CMYKCustomColor: 0 1 0 0 (CutContour)")
                endcomments = True
            if(endcomments):
                sys.stdout.write(line.replace("1 0 0 rg","0 1 0 0 (CutContour) findcmykcustomcolor 1 setcustomcolor"))
            else:
                sys.stdout.write(line)
