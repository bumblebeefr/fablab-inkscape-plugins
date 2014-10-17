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

# class MyEffect(inkex.Effect):
#   def __init__(self):
#     inkex.Effect.__init__(self)
#     self.OptionParser.add_option("--tab",
#                       action="store", type="string",
#                       dest="tab")
# 
#   def output(self):
#       pass
# 
#   def effect(self):
#     print_(sys.argv)
#     shutil.copyfile(sys.argv[2], "/tmp/tempfile.txt")
#     pass

if __name__ == '__main__':
    #shutil.copyfile(sys.argv[2], "/tmp/tempfile.txt")
    with open(sys.argv[2]) as f:
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
