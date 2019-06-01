# G-Code template handling
# This file is part of the opensoldering project distribution (https://github.com/swissembedded/opensolderingrobot.git).
# Copyright (c) 2019 by Daniel Haensse
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# some usefull info can be found here
# https://reprap.org/wiki/G-code

# Fill in parameters into template g-code
import math
from numpy import (array, dot, arccos, clip, subtract, arcsin, arccos)
from numpy.linalg import norm
import excellon

def complete_template(template, parameters):
    gcode=template.copy()
    for p, elem in enumerate(parameters):
        parameter=parameters[p]
        gcode.replace("%"+parameter.keys()[0], str(parameter.values()[0]))
    return gcode

# coordinate transformation
def get_printer_point(point, radians, scale, origin=(0, 0), translation=(0,0)):
    ### get printer point from nc drill coordinates
    x, y = point
    ox, oy = origin
    tx, ty = translation
    qx = tx + (math.cos(radians) * (x - ox) + math.sin(radians) * (y - oy))*scale
    qy = ty + (-math.sin(radians) * (x - ox) + math.cos(radians) * (y - oy))*scale
    return qx, qy

def panel_soldering(data, panelSelection, isTest):
    # header
    parameters={ "TravelX" : round(data['Setup']['TravelX'],5),
                 "TravelY" : round(data['Setup']['TravelY'],5),
                 "TravelZ" : round(data['Setup']['TravelZ'],5)}
    gcode = complete_template(data['GHeader'],parameters)
    # soldering backside?
    if data('SolderSide')=="Top":
        flip=1
    else:
        flip=-1
    # for each selected panel soldering
    for p, elem in enumerate(panelSelection):
        panel=data['Panel'][p]
        # get panel data
        # teached panel coordinates
        xp1=panel['RefX1']
        yp1=panel['RefY1']
        zp1=panel['RefZ1']
        xp2=panel['RefX2']
        yp2=panel['RefY2']
        zp2=panel['RefZ2']
        zp=(zp1+zp2)/2.0
        # solder toolpath
        soldertoolpath=data['SolderToolpath']
        refNum1=excellon.get_reference_1(soldertoolpath)
        ref1=soldertoolpath[refNum1]
        xn1=ref1['NCPositionX']
        yn1=ref1['NCPositionY']
        refNum2=excellon.get_reference_2(soldertoolpath)
        ref2=soldertoolpath[refNum2]
        xn2=ref2['NCPositionX']
        yn2=ref2['NCPositionY']
        # calculate transformation
        vp1=array([xp1,yp1])
        vn1=array([xn1,yn1])
        vp2=array([xp2,yp2])
        vn2=array([xn2,yn2])
        dvp=subtract(vp2,vp1)
        dvn=subtract(vn2,vn1)
        vplen=norm(dvp)
        vnlen=norm(dvn)
        c = dot(dvp,dvn)/(vplen*vnlen)
        radians = arccos(c)
        scale = vplen / vnlen
        # iterate over each solder point in the toolpath
        for s in range(get_number_solderpoints(soldertoolpath)):
            stp=get_solderpoint(s)
            xn=stp['NCPositionX']*flip
            yn=stp['NCPositionY']
            vn=array[xn, yn]
            sp=data['SolderingProfile'][stp['SolderingProfile']]
            xp, yp = get_printer_point(vn, -radians, scale, vn1, vp1)
            # create parameterlist
            parameters={
                    "TravelZ" : round(sp['TravelZ'],5),
                    "ApproxX" : round(xp-sp['ApproxOffsetX'],5),
                    "ApproxY" : round(yp-sp['ApproxOffsetY'],5),
                    "ApproxZ" : round(zp-sp['ApproxOffsetZ'],5),
                    "SolderX" : round(xp-sp['SolderOffsetX'],5),
                    "SolderY" :round(yp-sp['SolderOffsetY'],5),
                    "SolderZ" : round(zp-sp['SolderOffsetZ'],5),
                    "Heatup" : sp['Heatup'],
                    "SolderLength" : sp['SolderLength'],
                    "Melting" : sp['Melting'] }
            if isTest:
                gpos = complete_template(data['GSoldertest'], parameters)
            else:
                gpos = complete_template(data['GSolder'], parameters)
            g_code+=gpos
        gcode = complete_template(data['GFooter'], {})
        return gcode

def go_xyz(data, x,y,z):
    parameters = { "CoordX": x, "CoordY" : y, "CoordZ" : z }
    gcode = complete_template(gpos, data['GGo'], parameters)
    return gcode

def go_home(data):
    gcode = complete_template(data['GHome'], {})
    return gcode

# convert gcode into an array of single commands
def make_array(gcode):
    return gcode.splitlines()
