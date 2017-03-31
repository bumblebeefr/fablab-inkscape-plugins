# encoding: utf-8
import math


class BoxGenrationError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class BoxEffect():

    def tabs(self, length, tab_width, thickness, direction=0, **args):
        '''
             * Genere les elements d'un polygone
             * svg pour des encoche d'approximativement
             * <tab_width>, sur un longueur de <length>,
             * pour un materiau d'epaisseur <thickness>.
             *
             * Options :
             *  - direction : 0 haut de la face, 1 droite de la face, 2 bas de la face, 3 gauche de la face.
             *  - firstUp : Indique si l'on demarre en haut d'un crenau (true) ou en bas du crenau (false - defaut)
             *  - lastUp : Indique si l'on fin en haut d'un crenau (true) ou en bas du crenau (false - defaut)
        '''
        # Calcultate tab size and number

        tab_width = max(1.5*thickness, tab_width)
        nb_tabs = math.floor(length / tab_width)
        nb_tabs = int(nb_tabs - 1 + (nb_tabs % 2))
        tab_real_width = length / nb_tabs

        # Check if no inconsistency on tab size and number
        #print("Pour une largeur de %s et des encoches de %s => Nombre d'encoches : %s Largeur d'encoche : %s" % (length, tab_width, nb_tabs, tab_real_width))
        if (tab_real_width <= thickness * 1.5):
            raise BoxGenrationError("Attention les encoches resultantes (%.2f mm) ne sont pas assez larges au vue de l'epasseur de votre materiaux. Merci d'augmenter la largeur des encoches." % (tab_real_width, ))

    #     if (nb_tabs <= 1):
    #         raise BoxGenrationError("Attention vous n'aurez aucune encoche sur cette longeur, c'est une mauvaise idée !!! Indiquez une taill d'encoche correcte pour votre taille de boite")

        return self._rotate_path(self._generate_tabs_path(tab_real_width, nb_tabs, thickness, direction=direction, **args), direction)

    def _generate_tabs_path(self, tab_width, nb_tabs, thickness, cutOff=False, inverted=False, firstUp=False, lastUp=False, backlash=0, **args):
        # if (cutOff):
            #print("Generation d'un chemin avec l'option cuttOff")
        # else:
            #print("Generation d'un chemin sans l'option cuttOff")

        points = []
        for i in range(1, nb_tabs + 1):
            if(inverted):
                if(i % 2 == 1):  # gap
                    if(not firstUp or i != 1):
                        points.append([0, thickness])

                    if(i == 1 or i == nb_tabs):
                        points.append([tab_width - [0, thickness][cutOff] - (0.5 * backlash), 0])
                    else:
                        points.append([tab_width - backlash, 0])

                    if (i != nb_tabs or not lastUp):
                        points.append([0, -thickness])

                else:  # tab
                    points.append([tab_width + backlash, 0])

            else:
                if(i % 2 == 1):  # tab
                    if(not firstUp or i != 1):
                        points.append([0, -thickness])

                    if(i == 1 or i == nb_tabs):
                        points.append([tab_width - [0, thickness][cutOff] + (0.5 * backlash), 0])
                    else:
                        points.append([tab_width + backlash, 0])

                    if (i != nb_tabs or not lastUp):
                        points.append([0, thickness])

                else:  # gap
                    points.append([tab_width - backlash, 0])

        return points

    def _rotate_path(self, points, direction):
        if direction == 1:
            return [[-point[1], point[0]] for point in points]

        elif direction == 2:
            return [[-point[0], -point[1]] for point in points]

        elif direction == 3:
            return [[point[1], -point[0]] for point in points]
        else:
            return points

    def mm2u(self, arr):
        '''
        Translate a value or an array of values form 'mm' to document unit
        '''
        if type(arr) is list:
            return [self.mm2u(coord) for coord in arr]
        else:
            return self.unittouu("%smm" % arr)

    def toPathString(self, arr, end=" z"):
        return "m %s%s" % (' '.join([','.join([str(c) for c in pt]) for pt in arr]), end)

    def getPath(self, path, path_id, _x, _y, bg, fg):
        style = ''
        if(bg):
            style += "fill:%s;" % bg
        else:
            style += "fill:none;"
        if(fg):
            style += "stroke:%s;" % fg
        return {
            'style': style,
            'id': path_id,
            'transform': "translate(%s,%s)" % (_x, _y),
            'd': path
        }

    def _bottom(self, width, depth, tab_width, thickness, backlash):
        # print("_bottom")
        points = [[0, 0]]
        points.extend(self.tabs(width, tab_width, thickness,
                                direction=0,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True
                                ))
        points.extend(self.tabs(depth, tab_width, thickness,
                                direction=1,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True
                                ))
        points.extend(self.tabs(width, tab_width, thickness,
                                direction=2,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True
                                ))
        points.extend(self.tabs(depth, tab_width, thickness,
                                direction=3,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True
                                ))
        return points

    def _front_without_top(self, width, height, tab_width, thickness, backlash):
        # print("_front_without_top")
        points = [[0, 0], [width, 0]]
        points.extend(self.tabs(height - thickness, tab_width, thickness,
                                direction=1,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True
                                ))
        points.extend(self.tabs(width, tab_width, thickness,
                                direction=2,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True,
                                inverted=True
                                ))
        points.extend(self.tabs(height - thickness, tab_width, thickness,
                                direction=3,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True
                                ))
        return points

    def _front_with_top(self, width, height, tab_width, thickness, backlash):
        # print("_front_with_top")
        points = [[0, thickness]]

        points.extend(self.tabs(width, tab_width, thickness,
                                direction=0,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True,
                                inverted=True
                                ))
        points.extend(self.tabs(height - (thickness * 2), tab_width, thickness,
                                direction=1,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True
                                ))
        points.extend(self.tabs(width, tab_width, thickness,
                                direction=2,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True,
                                inverted=True
                                ))
        points.extend(self.tabs(height - (thickness * 2), tab_width, thickness,
                                direction=3,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True
                                ))
        return points

    def _side_without_top(self, depth, height, tab_width, thickness, backlash):
        # print("_side_without_top")
        points = [[thickness, 0], [depth - (4 * thickness), 0]]
        points.extend(self.tabs(height - thickness, tab_width, thickness,
                                direction=1,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True,
                                inverted=True
                                ))
        points.extend(self.tabs(depth, tab_width, thickness,
                                direction=2,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True,
                                inverted=True,
                                cutOff=True
                                ))
        points.extend(self.tabs(height - thickness, tab_width, thickness,
                                direction=3,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True,
                                inverted=True
                                ))
        return points

    def _side_with_top(self, depth, height, tab_width, thickness, backlash):
        # print("_side_with_top")
        points = [[thickness, thickness]]
        points.extend(self.tabs(depth, tab_width, thickness,
                                direction=0,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True,
                                inverted=True,
                                cutOff=True
                                ))
        points.extend(self.tabs(height - (2 * thickness), tab_width, thickness,
                                direction=1,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True,
                                inverted=True
                                ))
        points.extend(self.tabs(depth, tab_width, thickness,
                                direction=2,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True,
                                inverted=True,
                                cutOff=True
                                ))
        points.extend(self.tabs(height - (2 * thickness), tab_width, thickness,
                                direction=3,
                                backlash=backlash,
                                firstUp=True,
                                lastUp=True,
                                inverted=True
                                ))
        return points

    def box_with_top(self, prefix, _x, _y, bg, fg, width, depth, height, tab_size, thickness, backlash):
        paths = []
        paths.append(self.getPath(self.toPathString(self.mm2u(self._bottom(width, depth, tab_size, thickness, backlash))), '%s_bottom' % prefix, _x + self.mm2u(1 * thickness), _y + self.mm2u(1 * thickness), bg, fg))
        paths.append(self.getPath(self.toPathString(self.mm2u(self._bottom(width, depth, tab_size, thickness, backlash))), '%s_top' % prefix, _x + self.mm2u(2 * thickness + width), _y + self.mm2u(1 * thickness), bg, fg))
        paths.append(self.getPath(self.toPathString(self.mm2u(self._front_with_top(width, height, tab_size, thickness, backlash))), '%s_font' % prefix, _x + self.mm2u(2 * thickness + width), _y + self.mm2u(2 * thickness + depth), bg, fg))
        paths.append(self.getPath(self.toPathString(self.mm2u(self._front_with_top(width, height, tab_size, thickness, backlash))), '%s_back' % prefix, _x + self.mm2u(1 * thickness), _y + self.mm2u(2 * thickness + depth), bg, fg))
        paths.append(self.getPath(self.toPathString(self.mm2u(self._side_with_top(depth, height, tab_size, thickness, backlash))), '%s_left_side' %
                                  prefix, _x + self.mm2u(2 * thickness + depth), _y + self.mm2u(3 * thickness + depth + height), bg, fg))
        paths.append(self.getPath(self.toPathString(self.mm2u(self._side_with_top(depth, height, tab_size, thickness, backlash))), '%s_right_side' % prefix, _x + self.mm2u(1 * thickness), _y + self.mm2u(3 * thickness + depth + height), bg, fg))
        return paths

    def box_without_top(self, prefix, _x, _y, bg, fg, width, depth, height, tab_size, thickness, backlash):
        paths = []
        paths.append(self.getPath(self.toPathString(self.mm2u(self._bottom(width, depth, tab_size, thickness, backlash))), '%s_bottom' % prefix, _x + self.mm2u(1 * thickness), _y + self.mm2u(1 * thickness), bg, fg))
        paths.append(self.getPath(self.toPathString(self.mm2u(self._front_without_top(width, height, tab_size, thickness, backlash))), '%s_font' % prefix, _x + self.mm2u(2 * thickness + width), _y + self.mm2u(2 * thickness + depth), bg, fg))
        paths.append(self.getPath(self.toPathString(self.mm2u(self._front_without_top(width, height, tab_size, thickness, backlash))), '%s_back' % prefix, _x + self.mm2u(1 * thickness), _y + self.mm2u(2 * thickness + depth), bg, fg))
        paths.append(self.getPath(self.toPathString(self.mm2u(self._side_without_top(depth, height, tab_size, thickness, backlash))), '%s_left_side' %
                                  prefix, _x + self.mm2u(2 * thickness + depth), _y + self.mm2u(3 * thickness + depth + height), bg, fg))
        paths.append(self.getPath(self.toPathString(self.mm2u(self._side_without_top(depth, height, tab_size, thickness, backlash))), '%s_right_side' % prefix, _x + self.mm2u(1 * thickness), _y + self.mm2u(3 * thickness + depth + height), bg, fg))
        return paths
