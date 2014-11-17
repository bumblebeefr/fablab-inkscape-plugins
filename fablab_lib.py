# encoding: utf-8
from contextlib import contextmanager
import os
import tempfile

import cubicsuperpath
import simplepath
import simpletransform
import bezmisc
import cspsubdiv
import inkex
import platform

if "windows" not in platform.system().lower():
    from fablab_sh_lib import inkscape
    from fablab_sh_lib import convert
else:
    from fablab_pbs_lib import inkscape
    from fablab_pbs_lib import convert


@contextmanager
def tmp_file(ext, text=True):
    '''
        Create a temporary file to work on, pass it path, then remove it from the system.
        Example:

        with tmp_file(".txt") as tmp:
            print(tmp)
    '''
    fd, tmp = tempfile.mkstemp(ext, text=True)
    os.close(fd)
    try:
        yield tmp
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def print_(*arg):
    '''
        Print out debug message on fablab_debug.log in inkscape extension directory.
    '''
    f = open("fablab_debug.log", "a")
    for s in arg:
        s = str(unicode(s).encode('unicode_escape')) + " "
        f.write(s)
    f.write("\n")
    f.close()


def path_to_segments(node):
    '''
        Generator to convert a path node to an interator to og segmented path.
    '''
    mat = simpletransform.composeParents(node, [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    d = node.get('d')

    if len(simplepath.parsePath(d)) == 0:
        return

    p = cubicsuperpath.parsePath(d)
    simpletransform.applyTransformToPath(mat, p)

    # p is now a list of lists of cubic beziers [ctrl p1, ctrl p2, endpoint]
    # where the start-point is the last point in the previous segment

    for sp in p:
        path = []
        subdivideCubicPath(sp, 0.2)  # TODO: smoothness preference
        for csp in sp:
            path.append([csp[1][0], csp[1][1]])
        yield path


def subdivideCubicPath(sp, flat, i=1):
    """
    Break up a bezier curve into smaller curves, each of which
    is approximately a straight line within a given tolerance
    (the "smoothness" defined by [flat]).

    This is a modified version of cspsubdiv.cspsubdiv(). From Openscad plugins
    """

    while True:
        while True:
            if i >= len(sp):
                return

            p0 = sp[i - 1][1]
            p1 = sp[i - 1][2]
            p2 = sp[i][0]
            p3 = sp[i][1]

            b = (p0, p1, p2, p3)

            if cspsubdiv.maxdist(b) > flat:
                break

            i += 1

        one, two = bezmisc.beziersplitatt(b, 0.5)
        sp[i - 1][2] = one[1]
        sp[i][0] = two[2]
        p = [one[2], one[3], two[1]]
        sp[i:1] = [p]


class BaseEffect(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)

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
                os.remove(tmp)
            except(OSError):
                pass

    @contextmanager
    def reloaded_from_file(self, tmp):
        old_document = self.document
        self.parse(tmp)
        self.getposinlayer()
        self.getselected()
        self.getdocids()
        try:
            yield
        finally:
            self.document = old_document
            self.getposinlayer()
            self.getselected()
            self.getdocids()

    @contextmanager
    def inkscaped(self, arguments=[]):
        with self.as_tmp_svg() as tmp:
            ink_args = ["--file", tmp] + arguments + ["--verb=FileSave", "--verb=FileClose"]
            inkscape(*ink_args)
            with self.reloaded_from_file(tmp):
                yield tmp
