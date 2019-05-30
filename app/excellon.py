# Gerber / Excellon handling
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

import gerber
from gerber.render.cairo_backend import GerberCairoContext
from operator import sub
from gerber.excellon import DrillHit
from tsp_solver.greedy import solve_tsp

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
        hit[h]=ncdata.hits[h]
        tool = hit.tool.number
        pos=hit.position
        soldertoolpath.append(
            {# use index as id
             "NCId" : h,
             "NCPositionX": pos.x,
             "NCPositionY": pos.y,
             "NCTool" : tool,
             "PanelRef1": False, 
             "PanelRef2":False, 
             # no soldering
             "SolderingProfile": -1}
             # not sorted
             "ToolPathSorting":-1)
    print(soldertoolpath)
    return soldertoolpath

# get reference point 1 index
def get_reference_1(soldertoolpath):
    for e, elem in enumerate(soldertoolpath):
        if soldertoolpath[e]['PanelRef1'] == True:
            return e
    return -1

# get reference point 2 index
def get_reference_2(soldertoolpath):
    for e, elem in enumerate(soldertoolpath):
        if soldertoolpath[e]['PanelRef2'] == True:
            return e
    return -1

# optimize selected drill holes for best toolpath, beginning with reference 1
def optimize_soldertoolpath(soldertoolpath,ncdata)
    # unlike nc drill, we do not have to change tool, thus, we make a global optimization
    # we start on the first marker and search nearest neighbour
    neighbourX=0
    neighbourY=0
    for e, elem in enumerate(solderingtoolpath):
        tp=solderingtoolpath[e]
        if tp['PanelRef1']=True:
            tp['ToolPathSorting']=0
            neighbourX=tp['NCPositionX']
            neighbourY=tp['NCPositionY']
            print(0,solderingtoolpath[nearestIndex])
        else:
            tp['ToolPathSorting']=-1
    # sorting against neighbour
    hasUnSorted=True
    sortingIndex=1
    while hasUnsorted==True:
        nearestIndex=-1
        nearestDistance=-1.0
        for e, elem in enumerate(solderingtoolpath):
            tp=solderingtoolpath[e]
            if tp['ToolPathSorting']==-1 AND tp['SolderingProfile']>-1:
                posX=tp['NCPositionX']
                posY=tp['NCPositionY']
                distance=abs(neighboutX-posX)+abs(neighboutY-posY)
                if nearestDistance == -1 OR nearestDistance > distance:
                    nearestIndex=e
                    nearestDistance=distance
        # choose the best
        if nearestDistance == -1.0:
            hasUnSorted=False
        else:
            solderingtoolpath[nearestIndex]['ToolPathSorting']=sortingIndex
            posX=solderingtoolpath[nearestIndex]['NCPositionX']
            posY=solderingtoolpath[nearestIndex]['NCPositionY']
            print(sortingIndex,solderingtoolpath[nearestIndex])
            sortingIndex+=1

