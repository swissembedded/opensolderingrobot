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
    for hit in ncdata.hits:
        tool = hit.tool.number
        pos=hit.position
        print(tool, pos)
        soldertoolpath.append(
            {# use pos as key
             "NCPosition" : pos,
             "NCTool" : tool,
             "PanelRef1": False, 
             "PanelRef2":False, 
             # no soldering
             "SolderingProfile": -1})
    return soldertoolpath

def get_reference_1(soldertoolpath):
    return [element for element in soldertoolpath if element['PanelRef1'] == True]

def get_reference_2(soldertoolpath):    
    return [element for element in soldertoolpath if element['PanelRef2'] == True]


# optimize selected drill holes for best toolpath, beginning with reference 1
def optimize_soldertoolpath(soldertoolpath,ncdata)
    # unlike nc drill, we do not have to change tool, thus, we make a global optimization
    # we start on the first marker and search nearest neighbour
    first=get_reference_1(soldertoolpath)
    posfirst=first['NCPosition']
    sorted=[first]
    tmppath=soldertoolpath.copy()
    # iterate over the list
    while(size(tmppath):
        for e in tmppath:
            last = sorted[-1]
            poslast = last['NCPosition']
            possolder=solder['NCPosition']
            if possolder!=posfirst:
                ncdata.hits[last['NCPosition']]
                ncdata.hits[solder['NCPosition']]
                