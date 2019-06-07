# Data structure init, load, save for the project
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

import json
import string

def helper_read_json(name):
    with open(name+".json", 'r') as f:
        jsondata = json.load(f)
        return jsondata

def helper_read_txt(name):
    with open(name+".txt", 'r') as f:
        txtdata = f.read()
        return txtdata

# create data structure for new project
def init_project_data():
    data = {
            # read profile for camera
            "Setup": helper_read_json("setup"), # load setup from setup.json on new project or changes from connect
            # read soldering profiles
            "SolderingProfile" : helper_read_json("solderingprofile"),
            "SelectedSolderingProfile" : 0, # take first entry ListPopup on new project
            # CADMode
            "CADMode" : "Selection",
            # NC Drill
            "NCTool": {},
            # read g-code templates
            "GHome" : helper_read_txt("printerhome"),
            "GHeader" : helper_read_txt("printerheader"),
            "GSolder" : helper_read_txt("printersolder"),
            "GSoldertest" : helper_read_txt("printersoldertest"),
            "GFooter": helper_read_txt("printerfooter"),
            "GGo": helper_read_txt("printergo"),
            "GGetCoords": helper_read_txt("printergetcoords"),
            "GSpool" : "", # generated g-code for the panel soldering, created on print
            # panel definition
            "Panel": [
                        # array with panels, coordinates in 3d printer bed coordinates, teached in with panel menu
                        #{"RefX1" : 0, "RefY1":0, "RefZ1":"0", # x1/y1/z1 is first reference point
                        # "RefX2":1, "RefY2":2, "RefZ2":0 # x2/y2/z2 is second reference point
                        #}
                        ],
            # soldering toolpath
            "SolderToolpath": [ # array with soldering points, referencing nc drill tool and position in list, selected soldering profile, attributes if reference point
                        # sort this array with PanelRef1 first, following closest neigbourst on optimize soldering points, do not sort imported nc hits and nc tools
                        # { "NCId" : 0, "NCPositionX": 0, "NCPositionY": 0, "NCDiameter":0, "NCTool":0, "PanelRef1": True, "PanelRef2":False, "SolderingProfile":-1, "ToolPathSorting" }
                        ],
            # excellon
            "SolderSide": "Top", # let user choose on import of nc file
        }
    return data

def read_project_data(name):
    if name.endswith('.json') == False:
        name=name+".json"
    with open(name, 'r') as f:
        prjdata = json.load(f)
    return prjdata

def write_project_data(name, prjdata):
    if name.endswith('.json') == False:
        name=name+".json"
    with open(name, 'w') as f:
        json.dump(prjdata, f, indent=4, sort_keys=True)
