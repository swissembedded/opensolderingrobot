# Gerber / Excellon handling
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

import gerber
from gerber.render.cairo_backend import GerberCairoContext
from operator import sub
from gerber.excellon import DrillHit

# load nc drill, exception must be handled outside
def load_nc_drill(name):
    # Read gerber and Excellon files
    ncdata = gerber.read(name)
    #assume 3d printer to be metric
    ncdata.to_metric()
    return ncdata

# fill up data structure with nc drill
def convert_to_tools(ncdata):
    tools=[]
    for tool in iter(ncdata.tools.values()):
        tools.append(str(tool.number) + " : " + str(tool.diameter) + "mm")
    return tools

# fill up data structure with nc drill
def convert_to_json(ncdata):
    soldertoolpath = []
    positions   = {}
    tools   = {}

    #Get hit positions
    for h, elem in enumerate(ncdata.hits):
        hit = ncdata.hits[h]
        tool = hit.tool.number
        x,y = hit.position
        dia = hit.tool.diameter
        soldertoolpath.append(
            {# use index as id
             "NCId" : h,
             "NCPositionX": x,
             "NCPositionY": y,
             "NCTool" : tool,
             "NCDiameter": dia,
             "PanelRef1": False,
             "PanelRef2":False,
             # no soldering
             "SolderingProfile": -1,
             # not sorted
             "ToolPathSorting":-1})
    return soldertoolpath

# select all drill holes with certain tool (diameter)
def select_by_tool(soldertoolpath, tool, solderingprofile):
    for e, elem in enumerate(soldertoolpath):
        tp=soldertoolpath[e]
        if soldertoolpath[e]['NCTool']==tool:
            soldertoolpath[e]['SolderingProfile']=solderingprofile

# get the soldertoolpath index by position
def helper_get_index_by_position(soldertoolpath, x, y):
    nearestIndex=-1
    nearestDistance=-1
    for e, elem in enumerate(soldertoolpath):
        tp=soldertoolpath[e]
        posX=tp['NCPositionX']
        posY=tp['NCPositionY']
        distance=abs(x-posX)+abs(y-posY)
        if nearestDistance==-1 or distance < nearestDistance:
            nearestIndex=e
            nearestDistance=distance
    return nearestIndex


# select all drill holes with certain tool (diameter)
def select_by_position(soldertoolpath, x, y, solderingprofile):
    nearestIndex=helper_get_index_by_position(soldertoolpath, x, y)
    if nearestIndex!=-1:
       soldertoolpath[nearestIndex]['SolderingProfile']=solderingprofile

def deselect_by_position(soldertoolpath, x, y):
    nearestIndex=helper_get_index_by_position(soldertoolpath, x, y)
    if nearestIndex!=-1:
       soldertoolpath[nearestIndex]['SolderingProfile']=-1

# get reference point 1 index
def get_reference_1(soldertoolpath):
    for e, elem in enumerate(soldertoolpath):
        if soldertoolpath[e]['PanelRef1'] == True:
            return e
    return -1

# set reference point 1 index
def set_reference_1(soldertoolpath,x,y):
    oldref=get_reference_1(soldertoolpath)
    if oldref !=-1:
        soldertoolpath[e]['PanelRef1']=False
    nearestIndex=helper_get_index_by_position(soldertoolpath, x, y)
    if nearestIndex!=-1:
        soldertoolpath[nearestIndex]['PanelRef1']=True
        soldertoolpath[nearestIndex]['PanelRef2']=False

# get reference point 2 index
def get_reference_2(soldertoolpath):
    for e, elem in enumerate(soldertoolpath):
        if soldertoolpath[e]['PanelRef2'] == True:
            return e
    return -1

# set reference point 2 index
def set_reference_2(soldertoolpath,x,y):
    oldref=get_reference_2(soldertoolpath)
    if oldref !=-1:
        soldertoolpath[e]['PanelRef2']=False
    nearestIndex=helper_get_index_by_position(soldertoolpath, x, y)
    if nearestIndex!=-1:
        soldertoolpath[nearestIndex]['PanelRef1']=False
        soldertoolpath[nearestIndex]['PanelRef2']=True


# get number of selected solderpoint
def get_number_selected_solderpoints(soldertoolpath):
    num=0
    for e, elem in enumerate(soldertoolpath):
        if soldertoolpath[e]['SolderingProfile'] !=-1:
            num+=1
    return num

# get solder point by index
def get_solderpoint(soldertoolpath, index):
    for e, elem in enumerate(soldertoolpath):
        if soldertoolpath[e]['ToolPathSorting'] == index:
            return e
    return -1

# get number of solderpoint
def get_number_solderpoints(soldertoolpath):
    num=-1
    for e, elem in enumerate(soldertoolpath):
        sort = soldertoolpath[e]['ToolPathSorting']
        if sort > num:
            num=sort
    return num+1

# return the number of soldering points that are not optimized yet
def helper_get_number_of_unsorted(soldertoolpath):
    num=0
    for e, elem in enumerate(soldertoolpath):
        tp=soldertoolpath[e]
        if tp['ToolPathSorting']==-1 and tp['SolderingProfile']!=-1:
            num+=1
    return num

# optimize selected drill holes for best toolpath, beginning with reference 1
def optimize_soldertoolpath(soldertoolpath):
    # unlike nc drill, we do not have to change tool, thus, we make a global optimization
    # we start on the first marker and search nearest neighbour
    neighbourX=0
    neighbourY=0
    hasFirst=False
    hasSecond=False
    for e, elem in enumerate(soldertoolpath):
        tp=soldertoolpath[e]
        if tp['PanelRef1']==True:
            tp['ToolPathSorting']=0
            neighbourX=tp['NCPositionX']
            neighbourY=tp['NCPositionY']
            hasFirst=True
        else:
            tp['ToolPathSorting']=-1
            if tp['PanelRef2']==True:
                hasSecond=True
    if hasFirst==False:
        print("warning no first reference point available")
        return 0
    if hasSecond==False:
        print("warning no second reference point available")
        return 0

    # sorting against neighbour
    sortingIndex=1
    while helper_get_number_of_unsorted(soldertoolpath)>0:
        nearestIndex=-1
        nearestDistance=-1.0
        for e, elem in enumerate(soldertoolpath):
            tp=soldertoolpath[e]
            if tp['ToolPathSorting']==-1 and tp['SolderingProfile']!=-1:
                posX=tp['NCPositionX']
                posY=tp['NCPositionY']
                distance=abs(neighbourX-posX)+abs(neighbourY-posY)
                if nearestDistance == -1 or nearestDistance > distance:
                    nearestIndex=e
                    nearestDistance=distance
        # choose the best
        if nearestDistance != -1.0:
            soldertoolpath[nearestIndex]['ToolPathSorting']=sortingIndex
            neighbourX=soldertoolpath[nearestIndex]['NCPositionX']
            neighbourY=soldertoolpath[nearestIndex]['NCPositionY']
            #print(sortingIndex,soldertoolpath[nearestIndex])
            sortingIndex+=1

# Get nc tool area
def get_nc_tool_area(soldertoolpath):
    xmin=0
    xmax=0
    ymin=0
    ymax=0
    for e, elem in enumerate(soldertoolpath):
        tp=soldertoolpath[e]
        xemin=tp['NCPositionX']-(tp['NCDiameter']/2.0)
        xemax=tp['NCPositionX']+(tp['NCDiameter']/2.0)
        yemin=tp['NCPositionY']-(tp['NCDiameter']/2.0)
        yemax=tp['NCPositionY']+(tp['NCDiameter']/2.0)
        if e==0 or xemin<xmin:
            xmin=xemin
        if e==0 or xemax>xmax:
            xmax=xemax
        if e==0 or yemin<ymin:
            ymin=yemin
        if e==0 or yemax>ymax:
            ymax=yemax
    return xmin, xmax, ymin, ymax

# Get nc tool position from click
def get_nc_tool_position(soldertoolpath,x,y,w,h):
    xmin, xmax, ymin, ymax=get_nc_tool_area(soldertoolpath)
    xt=(x/w*(xmax-xmin))+xmin
    yt=(y/h*(ymax-ymin))+ymin
    return xt,yt

# Get nc tool position from click
def get_pixel_position(soldertoolpath,x,y,w,h):
    xmin, xmax, ymin, ymax=get_nc_tool_area(soldertoolpath)
    xt=(x-xmin)/(xmax-xmin)*w
    yt=(y-ymin)/(ymax-ymin)*h
    return xt,yt

# set the number of panel
def set_num_panel(panel, num):
    while len(panel)<num:
        panel.append({"RefX1" : -1, "RefY1":-1, "RefZ1":-1, "RefX2":-1, "RefY2":-1, "RefZ2":-1})

# get the number of panel
def get_num_panel(panel):
    return len(panel)

# get panel reference point 1
def get_panel_reference_1(panel,index):
    return panel[index]['RefX1'], panel[index]['RefY1'], panel[index]['RefZ1']

# set reference point 1
def set_panel_reference_1(panel,index,x,y,z):
    panel[index]['RefX1']=x
    panel[index]['RefY1']=y
    panel[index]['RefZ1']=z

# get panel reference point 2
def get_panel_reference_2(panel,index):
    return panel[index]['RefX2'], panel[index]['RefY2'], panel[index]['RefZ2']

# set reference point 2
def set_panel_reference_2(panel,index,x,y,z):
    panel[index]['RefX2']=x
    panel[index]['RefY2']=y
    panel[index]['RefZ2']=z

# get list of soldering profile
def get_list_soldering_profile(solderingprofile):
    profile=[]
    for p, elem in enumerate(solderingprofile['SolderingProfile']):
        profile.append(solderingprofile['SolderingProfile'][p]['Id'])
    return profile

# get item of soldering profile
def get_soldering_profile(solderingprofile, index):
    return solderingprofile['SolderingProfile'][index]
