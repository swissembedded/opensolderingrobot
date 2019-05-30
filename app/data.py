# return data structure for new project
import json
import string

def helper_read_json(name):
    with open(name+".json", 'r') as f:
        json = json.load(f)
        return json

def helper_read_txt(name):
    with open(name+".txt", 'r') as f:
        txt = f.read()
        return txt
        
def init_project_data():
    data = {
            # read profile for camera
            "Setup": helper_read_json("setup"), # load setup from setup.json on new project or changes from connect
            # read soldering profiles
            "SolderingProfile" : helper_read_json("solderingprofile")
            "SelectedSolderingProfile" : 0, # take first entry ListPopup on new project
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
                        # { "NCTool":0, "NCPosition":0, "PanelRef1": True, "PanelRef2":False, "SolderingProfile":"Weidmuller Conn Term"}
                        ]
            # excellon
            "NCSettings": helper_read_json("excellon"), # load settings from excellon.json
            "NCSolderSide": "Top", # let user choose on import of nc file
            "NCHits": {}, # generated on nc drill import
            "NCTools": {}, # generated on nc drill import
        }
    return data

def read_project_data(name):
    if name.endswith('.json') == False:
        name=name+".json"
    with open(name, 'r') as f:
        json = json.load(f)
        return json
        
def write_project_data(name, write):
    if name.endswith('.json') == False:
        name=name+".json"
     with open(name, 'w') as f:
        json.dump(write, f, indent=4, sort_keys=True)

