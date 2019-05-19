
############ Susanna edited #########

from time import time
from kivy.app import App
from os.path import dirname, join
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.screenmanager import Screen
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from kivy.uix.popup import Popup

from kivy.adapters.listadapter import ListAdapter
from kivy.uix.listview import ListItemButton, ListView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
# set the initial size
from kivy.config import Config

import os
import requests

# optmized drill path
import math
import gerber
from operator import sub
from gerber.excellon import DrillHit
from tsp_solver.greedy import solve_tsp

# list view for soldering profile
from kivy.adapters.listadapter import ListAdapter
from kivy.uix.listview import ListItemButton, ListView
import json

MAX_SIZE = (1280, 768)
Config.set('graphics', 'width', MAX_SIZE[0])
Config.set('graphics', 'height', MAX_SIZE[1])
Config.set('graphics', 'resizable', False)

#############################
# TODO clean up
screen = {"screen":"main"}
user= {"email":"", "pass":"" ,"name":""}
column= {"add":""}
download = {"download":""}
report = {"mail":""}
play_list = {"ID":"", "names":""}

status_current = {"download":"", "process":""}


# final videos list
final_list = {"video":"", "from_to":"", "output":""}
# for downloading list
downloading_list = []
# for processing list
processing_list = []

from_to_list = []
video_list = []
output_list = []

# data structure
data = {
            "Setup": {}, # load setup from setup.json on new project or changes from connect
            "SolderingProfile" : {}, # load profile from SolderingProfile.json on new project
            "SelectedSolderingProfile" : "", # take first entry SolderingProfile on new project
            "NCSettings": {}, # load settings from excellon.json on new project
            "NCHits": {}, # generated on nc drill import
            "NCTools": {}, # generated on nc drill import
            "GHome" : "", # g-code string loaded from printerhome.txt file on new project
            "GHeader" : "", # g-code string loaded from printerheader.txt file on new project
            "GSolder" : "", # g-code string loaded from printersolder.txt file on new project
            "GFooter": "", # g-code string loaded from printerfooter.txt file on new project
            "GSpool" : "", # generated g-code for the panel
            "Panel": [
                        # array with panels, coordinates in 3d printer bed coordinates, teached in with panel menu
                        #{"RefX1" : 0, "RefY1":0, "RefZ1":"0", # x1/y1/z1 is first reference point
                        # "RefX2":1, "RefY2":2, "RefZ2":0 # x2/y2/z2 is second reference point
                        #} 
                        ],
            "Solder": [ # array with soldering points, referencing nc drill tool and position in list, selected soldering profile, attributes if reference point
                        # sort this array with PanelRef1 first, following closest neigbourst on optimize soldering points, do not sort imported nc hits and nc tools
                        # { "NCTool":0, "NCPosition":0, "PanelRef1": True, "PanelRef2":False, "SolderingProfile":"Weidmuller Conn Term"}
                        ]
        }


def error_handling():
    return ('---UI---Error: {}  {}, line: {}'.format(sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno))

def assure_path_exists(path):
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)


########### Pop Up message #######
class UloginFail(Popup):
    def __init__(self, obj, **kwargs):
        super(UloginFail, self).__init__(**kwargs)
        self.obj = obj

class LoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)
class SaveDialog(FloatLayout):
    save = ObjectProperty(None)
    text_input = ObjectProperty(None)
    cancel = ObjectProperty(None)
class SolderingProfile(BoxLayout):
    pass
class ScreenManagement(ScreenManager):
    pass


class ListScreen(Screen):
    def __init__(self, **kwargs):
        super(ListScreen, self).__init__(**kwargs)
        self.b_init_soldering = True
        self.drill_file_path = "" # drill file path
        #Clock.schedule_interval(self.load_list, 0.2)
        #Clock.schedule_interval(self.show_status, 0.8)
    #### File menu
    def new_file(self):
        # erase(initialize) all data
        self.drill_file_path = ""
    def load_file(self):
        content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()
    def save_file(self):
        pass
    def save_as_file(self):
        content = SaveDialog(save=self.save, cancel=self.dismiss_popup)
        self._popup = Popup(title="Save file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()
    #### program menu ####
    def import_nc(self):
        content = LoadDialog(load=self.load_nc, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()
    
    def load_nc(self, path, filename):
        self.dismiss_popup()
        print(filename)
        self.optmize_nc(filename)
    
    def select_profile(self):
        
        with open('solderingprofile.json', 'r') as f:
            profile_data = json.load(f)
        items = []
        for i in range(len(profile_data["SolderingProfile"])):
            items.append(profile_data["SolderingProfile"][i]["Id"])

        self.content = SolderingProfile()
        list_adapter = ListAdapter(data=items,    cls=ListItemButton, selection_mode='single', allow_empty_selection=False)
        list_view = ListView(adapter=list_adapter)
        list_view.row_height = 160
        
        self.content.ids.profile_list.add_widget(list_view)
        #list_view.adapter.selection = ['USB Signals']
        list_view.adapter.bind(on_selection_change=self.selected_profile)
            

        self._popup = Popup(title="Select soldering profile", content=self.content,
                            size_hint=(0.5, 0.6))
        self._popup.open()

    def selected_profile(self, adapter):
        print(adapter.selection[0].text)
        self.dismiss_popup()
    def optmize_nc(self, path):
        print(path[0])  
        # Read the excellon file
        f = gerber.read(path[0])

        positions   = {}
        tools   = {}
        hit_counts = f.hit_count()
        oldpath = sum(f.path_length().values())

        #Get hit positions
        for hit in f.hits:
            tool_num = hit.tool.number
            if tool_num not in positions.keys():
                positions[tool_num]   = []
            positions[tool_num].append(hit.position)

        hits = []

        # Optimize tool path for each tool
        for tool, count in iter(hit_counts.items()):

            # Calculate distance matrix
            distance_matrix = [[math.hypot(*tuple(map(sub, 
                                                      positions[tool][i], 
                                                      positions[tool][j]))) 
                                for j in iter(range(count))] 
                                for i in iter(range(count))]

            # Calculate new path
            path = solve_tsp(distance_matrix, 50)

            # Create new hits list
            hits += [DrillHit(f.tools[tool], positions[tool][p]) for p in path]

        # Update the file
        f.hits = hits
        f.filename = f.filename + '.optimized'
        f.write()
        
        # Print drill report
        print(f.report())
        print('Original path length:  %1.4f' % oldpath)
        print('Optimized path length: %1.4f' % sum(f.path_length().values()))
    
    # select soldering pad by diameter
    # 1. dialog with tool selection
    # 2. add/update all nc drill with that tool in list "solder" with currently selected soldering program info

    # select soldering pad in view
    # 1. get click coordinate
    # 2. add / update nc drill with that coordinate in list "solder" with currently soldering program info

    # deselect soldering pad in view
    # 1. get click coordinate
    # 2. remove nc drill with that coordinate from list "solder"

    # set reference point 1 & 2
    # 1. get click coordinate
    # 2. add / update nc drill with that coordinate from list "solder" with attribute reference point 1 or 2

    # optimize solder point order
    # 1. pick reference point 1 as first point
    # 2. find nearest neighbour and iterate on each nearest neighbour until list is sorted

    # set number of panel
    # 1. show dialog to choose number of panel
    # 2. persist number in config

    # set reference point for panel
    # 1. dialog to choose panel number and and two buttons to teach reference point 1 or 2
    # 2. dialog to move printer on x,y,z, show coordinate, show previously teached reference point values, accept new value, cancel
    # 3. if accepted, update coordinate on panel n for reference point 1 or 2

    # connect printer
    # 1. dialog to choose printer device
    # 2. open port and send printerhome.txt

    # connect video
    # 1. dialog to choose video device
    # 2. show camera in camera tab

    # start soldering
    # 1. dialog to choose panel to solder, default all panels selected
    # 2. create g-code with header, soldering, footer and save it to file
    # 3. on button solder pressed, spool the file to the printer, so progress in status
    
    # pause soldering
    # 1. pause spooling until button clicked again

    # stop soldering
    # 1. stop spooling, send printerfooter file

    def dismiss_popup(self):
        self._popup.dismiss()

    

    def load(self, path, filename):
        with open(os.path.join(path, filename[0])) as stream:
            pass
            #self.text_input.text = stream.read()

        self.dismiss_popup()

    def save(self, path, filename):
        with open(os.path.join(path, filename), 'w') as stream:
            pass
            #stream.write(self.text_input.text)
        #print(os.path.join(path, filename))
        self.dismiss_popup()

    def show_status(self, dt):
        if  self.ids is not "":
            self.ids["lbl_cad_cam"].text = " Camera connected"  
            self.ids["lbl_solder_status"].text = " soldering 1/N pads on panel 2/M"

class MyApp(App):
    
    def check_resize(self, instance, x, y):
        # resize X
        if x > MAX_SIZE[0]:
            Window.size = (1280, Window.size[1])
        # resize Y
        if y > MAX_SIZE[1]:
            Window.size = (Window.size[0], 768)   
    def mainscreen(self):
        screen["screen"] = "main"
        
    def build(self):
        self.title = 'THT Soldering Robot'
        Window.size = (1280, 768)
        Window.bind(on_resize=self.check_resize)

        return ScreenManagement()


if __name__ == '__main__':
    Builder.load_file("main.kv")
    MyApp().run()
    