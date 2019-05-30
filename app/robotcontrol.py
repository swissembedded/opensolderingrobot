# G-Code template handling
# This file is part of the opensoldering project distribution (https://github.com/swissembedded/opensolderingrobot.git).
# Copyright (c) 2019 by Daniel Haensse
# Copyright (c) 2019 by Susanna
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

# Fill in parameters into template g-code
import math
from numpy import (array, dot, arccos, clip, subtract, arcsin, arccos)
from numpy.linalg import norm
import excellon

def complete_template(template, parameters):
    gcode=template
    for p, elem in enumerate(parameters):
        parameter=parameters[p]
        gcode.replace("%"+parameter.keys()[0], str(parameter.values()[0])
    return gcode 

# coordinate transformation
def get_printer_point(self, point, radians, scale, origin=(0, 0), translation=(0,0)):
    ### get printer point from nc drill coordinates
    x, y = point
    ox, oy = origin
    tx, ty = translation
    qx = tx + (math.cos(radians) * (x - ox) + math.sin(radians) * (y - oy))*scale
    qy = ty + (-math.sin(radians) * (x - ox) + math.cos(radians) * (y - oy))*scale
    return qx, qy   

  def panel_soldering(data, panelSelection, isTest):
        # header 
        gcode = complete_template(data['GHeader'])
        # soldering backside?
        if data('NCSolderSide')=="Top":
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
            for s in range(get_number_solderpoints(soldertoolpath))
                stp=get_solderpoint(s)
                xn=stp['NCPositionX']*flip
                yn=stp['NCPositionY']
                vn=array[xn, yn]
                sp=stp['SolderingProfile']
                xp, yp = get_printer_point(vn, -radians, scale, vn1, vp1)
                # create parameterlist
                parameters['TravelZ']=round(sp['TravelZ'],5)
                parameters['ApproxX']
                parameters['ApproxY']
                parameters['ApproxZ']
                parameters['SolderX']
                parameters['SolderY']
                parameters['SolderZ']
                parameters['Heatup']
                parameters['SolderLength']
                parameters['Melting']
                
                PosX=
                PosY = round((x0), 5), round((y0), 5)

if self.reference_printer["1"][k][0] == 0.0 and self.reference_printer["1"][k][1] == 0.0:
                continue
            if self.reference_printer["2"][k][0] == 0.0 and self.reference_printer["2"][k][1] == 0.0:
                continue
            # nc drill reference point
            xp1_0, yp1_0 = self.reference_1[0], self.reference_1[1]
            xp2_0, yp2_0 = self.reference_2[0], self.reference_2[1]
            
            backside=1 # set backside to -1 on bottom layer
            xp1=xp1_0*backside
            yp1=yp1_0
            
            # 3d printer reference point 1 for k' th panel
            x1, y1 = self.reference_printer["1"][k][0], self.reference_printer["1"][k][1]
            xp2=xp2_0*backside
            yp2=yp2_0
            
            # 3d printer reference point 2 for k' th panel
            x2, y2 = self.reference_printer["2"][k][0], self.reference_printer["2"][k][1]
            
            v1=array([x1,y1])
            vp1=array([xp1,yp1])
            v2=array([x2,y2])
            vp2=array([xp2,yp2])
            dv=subtract(v2,v1)
            dvp=subtract(vp2,vp1)
            vlen=norm(dv)
            vplen=norm(dvp)
            c = dot(dv,dvp)/(vlen*vplen)
            radians = arccos(c)
            scale = vlen / vplen

            if isTest:
                gpos = complete_template(data['GSoldertest'])
            else
                gpos = complete_template(data['GSolder'])

            data = gerber.read(self.sel_tool_path)
            data.to_metric()
            gcode.append("; panel " + str(k+1) + " start")
            for hit in data.hits:
                x, y = hit.position
                v2_1 = array([x, y])
                x0, y0 = array(self.get_printer_point(v2_1, -radians, scale, vp1, v1))
                # 3d printer points based on (left, bottom) == (0, 0)
                PosX, PosY = round((x0), 5), round((y0), 5)
                PosZ = 10 # reference point 1 and 2, z component average see above ????where is this value defined?

                self.ApproxX = round((PosX-self.ApproxOffsetX),5)
                self.ApproxY = round((PosY-self.ApproxOffsetY),5)
                self.ApproxZ = round((PosZ-self.ApproxOffsetZ),5)
                self.SolderX = round((PosX-self.SolderOffsetX),5)
                self.SolderY = round((PosY-self.SolderOffsetY),5)
                self.SolderZ = round((PosZ-self.SolderOffsetZ),5)

                #print(PosX, PosY, PosZ, SolderX, SolderY, SolderZ)
                gcode.extend(self.send_gcode_from_template(template))
        
        # header 
        gcode = complete_template(data['GFooter'])
        return gcode