#!/usr/bin/env python
# encoding: utf-8
import os
import sys
import simplestyle
import time

from fablab_lib import *


class PathToPolygon(BaseEffect):

    def __init__(self):
        BaseEffect.__init__(self)
        self.OptionParser.add_option(
            '--precision', action='store', type='float', default=0.2)

    def effect(self):
        for _id, node in self.selected.iteritems():
            if node.tag == inkex.addNS('path', 'svg'):
                d = ""
                for points in path_to_segments(node, self.options.precision):
                    d += "M %s " % " ".join(("%s,%s" %
                                             (p[0], p[1]) for p in points))

                node.set('d', d)
            else:
                inkex.errormsg(
                    " L'objet #%s n'est pas un chemin, il doit converti en chmein avant d'être converti en polyligne." % _id)


if __name__ == '__main__':
    PathToPolygon().affect(output=True)
