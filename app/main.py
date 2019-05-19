
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
from gerber.render.cairo_backend import GerberCairoContext
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

screen = {"screen":"main"}
# data structure
data = {
            "Setup": {}, # load setup from setup.json on new project or changes from connect
            "SolderingProfile" : {}, # load profile from SolderingProfile.json on new project
            "SelectedSolderingProfile" : "", # take first entry SolderingProfile on new project
            "NCSettings": {}, # load settings from excellon.json on new project
            "SolderingProfile" : {}, # load profile from SolderingProfile.json on new project
            "SelectedSolderingProfile" : "", # take first entry SolderingProfile on new project
            "NCSettings": {}, # load settings from excellon.json on new project
            "NCSolderSide": "Top", # let user choose on import of nc file if top or bottom is soldered, in case of bottom, mirror picture on screen on y axis.
            "NCHits": {}, # generated on nc drill import
            "NCTools": {}, # generated on nc drill import
            "GHome" : "", # g-code string loaded from printerhome.txt file on new project
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
        self.items = []
        self.current_profile = ""
        
        self.nc_file_path = ""
        self.drill_file_path = "" 
        self.cad_file_path = ""
        #Clock.schedule_interval(self.load_list, 0.2)
        #Clock.schedule_interval(self.show_status, 0.8)
    #### File menu
    def new_file(self):
        # erase(initialize) all data
        self.nc_file_path = ""
        self.drill_file_path = "" 
        self.cad_file_path = ""
        self.items = []
        self.current_profile = ""

        # init cad view
        self.ids["img_cad"].source = self.cad_file_path
        self.ids["img_cad"].reload()
        # init status bar
        self.ids["lbl_cad_cam"].text = ""  
        self.ids["lbl_solder_status"].text = ""

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
        self.nc_file_path = filename[0]
        # Read gerber and Excellon files
        data = gerber.read(self.nc_file_path)
        data.to_metric()
        # Rendering context
        ctx = GerberCairoContext(scale=1.0/0.1) # Scale is pixels/mm
        #self.optmize_nc(filename)
        # Create SVG image
        data.render(ctx)
        ctx.dump("temp.png")
        self.cad_file_path = "temp.png"
        self.ids["img_cad"].source = self.cad_file_path
        self.ids["img_cad"].reload()
    def select_profile(self):
        
        self.items.clear()
        with open('solderingprofile.json', 'r') as f:
            profile_data = json.load(f)
        
        for i in range(len(profile_data["SolderingProfile"])):
            if self.current_profile == profile_data["SolderingProfile"][i]["Id"]:
                dic_solder = {'text':profile_data["SolderingProfile"][i]["Id"], 'is_selected': True}
                self.b_init_soldering = False
            else:
                dic_solder = {'text':profile_data["SolderingProfile"][i]["Id"], 'is_selected': False}
            self.items.append(dic_solder)
        
        content = SolderingProfile()
        args_converter = lambda row_index, rec: {'text': rec['text'], 'is_selected': rec['is_selected'], 'size_hint_y': None, 'height': 50}
        list_adapter = ListAdapter(data=self.items, args_converter=args_converter, propagate_selection_to_data=True, cls=ListItemButton, selection_mode='single', allow_empty_selection=False)
        list_view = ListView(adapter=list_adapter)
        
        content.ids.profile_list.add_widget(list_view)
        
        list_view.adapter.bind(on_selection_change=self.selected_profile)
        
        
        self._popup = Popup(title="Select soldering profile", content=content,
                            size_hint=(0.5, 0.6))
        self._popup.open()

    def selected_profile(self, adapter):
        if self.b_init_soldering:
            self.ids.lbl_solder_status.text = adapter.selection[0].text
            self.current_profile = adapter.selection[0].text
            self.dismiss_popup()
        else:
            self.b_init_soldering = True

    def optmize_nc(self):
        if self.nc_file_path == "":
            return
        # Read the excellon file
        f = gerber.read(self.nc_file_path)

        positions   = {}
        tools   = {}
        hit_counts = f.hit_count()
        oldpath = sum(f.path_length().values())

        print(f.tools)
        print(f.settings)
        #Get hit positions
        for hit in f.hits:
            tool_num = hit.tool.number
            if tool_num not in positions.keys():
                positions[tool_num]   = []
            positions[tool_num].append(hit.position)

        hits = []
        """
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
        """
    
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
    