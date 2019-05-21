
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
# list view for soldering profile
from kivy.adapters.listadapter import ListAdapter
from kivy.uix.listview import ListItemButton, ListView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from kivy.graphics import Color, Rectangle, Line, Triangle, Ellipse
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


import json
from PIL import Image as pil_image

try:
    from cStringIO import StringIO
except(ImportError):
    from io import StringIO

MAX_SIZE = (1280, 768)
Config.set('graphics', 'width', MAX_SIZE[0])
Config.set('graphics', 'height', MAX_SIZE[1])
Config.set('graphics', 'resizable', False)

#############################
# TODO clean up
screen = {"screen":"main"}
real_img_size = {}
bound_box = {}
hit_info = []
sel_hit_info = []
# data structure
data = {
            "Setup": {}, # load setup from setup.json on new project or changes from connect
            "ListPopup" : {}, # load profile from ListPopup.json on new project
            "SelectedListPopup" : "", # take first entry ListPopup on new project
            "NCSettings": {}, # load settings from excellon.json on new project
            "ListPopup" : {}, # load profile from ListPopup.json on new project
            "SelectedListPopup" : "", # take first entry ListPopup on new project
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
                        # { "NCTool":0, "NCPosition":0, "PanelRef1": True, "PanelRef2":False, "ListPopup":"Weidmuller Conn Term"}
                        ]
        }

def assure_path_exists(path):
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)
class TouchImage(Image):

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            try:
                x_start, y_start = self.pos
                width, height = self.size
                ratio = height/real_img_size["height"]
                ratio_width = real_img_size["width"]*ratio
                x_delta = (width-ratio_width)/2
                x_start += x_delta
                
                x_end, y_end = x_start + ratio_width, y_start + height

                cur_x, cur_y = touch.pos
                if cur_x > x_start and cur_x < x_end and cur_y > y_start and cur_y < y_end:
                    b_exist, dia, (pos_x, pos_y) = self.get_dia_true(touch.pos, ratio, x_start, y_start)

                    if b_exist:
                        self.select_drill(pos_x, pos_y, dia)
            except:
                return True
            return True
        return super(TouchImage, self).on_touch_down(touch)
    def select_drill(self, pos_x, pos_y, dia):
        with self.canvas.after:
            x = pos_x - dia
            y = pos_y - dia
            Color(255/255, 0/255, 0/255)
            Ellipse(pos=(x, y), size=(2*dia, 2*dia))
            print(pos)
    def get_dia_true(self, pos, ratio, x_start, y_start):
        
        for i in range(len(hit_info)):
            x, y, radius, tool_num = hit_info[i]
            cur_x, cur_y = pos
            x_min = (x - radius - bound_box["x"])*ratio + x_start
            x_max = (x + radius - bound_box["x"])*ratio + x_start
            y_min = (y - radius - bound_box["y"])*ratio + y_start
            y_max = (y + radius - bound_box["y"])*ratio + y_start
            if cur_x > x_min and cur_x < x_max and cur_y > y_min and cur_y < y_max:
                pos_x = x_min + radius*ratio
                pos_y = y_min + radius*ratio
                print(x, y, radius)
                sel_hit_info.append((x/10, y/10, radius*2/10, tool_num))
                return True, radius*ratio, (pos_x, pos_y)
        return False, 0, (0, 0)
    def deselect_drill(self):
        self.canvas.after.clear()
        sel_hit_info.clear()
        
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
class ListPopup(BoxLayout):
    pass
class EditPopup(BoxLayout):
    save = ObjectProperty(None)
    cancel = ObjectProperty(None)
class ScreenManagement(ScreenManager):
    pass

class ListScreen(Screen):
    def __init__(self, **kwargs):
        super(ListScreen, self).__init__(**kwargs)
        self.b_init_soldering = True
        self.b_init_dia_tool = True
        self.items_soldering_profile = []
        self.item_nc_tools = []
        self.sel_soldering_profile = ""
        self.sel_dia_tool = ""
        
        
        self.nc_file_path = ""
        self.sel_tool_path = "" 
        self.cad_img_origin_path = ""
        self.cad_img_sel_path = ""

        ### setup settings
        self.setup_settings = ""
        self.sol_profile_settings = ""
        self.sel_sol_profile_settings = ""
        self.nc_settings = ""
        self.nc_hits = ""
        self.nc_tools = ""
        self.g_home = ""
        self.g_header = ""
        self.g_solder = ""
        self.g_footer = ""
        self.g_spool = ""
        self.panel_settings = ""
        self.solder_settings = ""

        #### port settings 
        self.cam_port = ""
        self.printer_port = ""
        Clock.schedule_interval(self.init_gui, 0.2)
        #Clock.schedule_interval(self.show_status, 0.8)
    def init_gui(self, dt):
        self.new_file()
        Clock.unschedule(self.init_gui)    
    #### File menu
    def new_file(self):
        self.init_project()

        # init cad view
        self.ids["img_cad_origin"].source = self.cad_img_origin_path
        self.ids["img_cad_origin"].reload()
        self.ids["img_cad_selected"].source = self.cad_img_sel_path
        self.ids["img_cad_selected"].reload()
        # init status bar
        self.ids["lbl_cad_cam"].text = ""  
        self.ids["lbl_solder_status"].text = self.sel_soldering_profile + " / " + self.sel_dia_tool
        
    def init_project(self):
        # erase(initialize) all data
        self.nc_file_path = ""
        self.sel_tool_path = "" 
        self.cad_img_origin_path = ""
        self.cad_img_sel_path = ""
        self.items_soldering_profile = []
        self.sel_soldering_profile = ""
        self.sel_dia_tool = ""

        with open('setup.json', 'r') as f:
            self.setup_settings = json.load(f)
        self.printer_port = self.setup_settings["RobotPort"]
        self.cam_port = self.setup_settings["CameraPort"]

        with open('solderingprofile.json', 'r') as f:
            self.sol_profile_settings = json.load(f)
        self.sel_soldering_profile = self.sol_profile_settings["SolderingProfile"][0]["Id"]
        self.sel_sol_profile_settings = self.sol_profile_settings["SolderingProfile"][0]

        with open('excellon.json', 'r') as f:
            self.nc_settings = json.load(f)
        self.nc_hits = ""
        self.nc_tools = ""

        with open("printerhome.txt", 'rU') as f:
            self.g_home = f.read()
        with open("printerheader.txt", 'rU') as f:
            self.g_header = f.read()
        with open("printerfooter.txt", 'rU') as f:
            self.g_footer = f.read()
        with open("printersolder.txt", 'rU') as f:
            self.g_solder = f.read()

        self.g_spool = ""
        self.panel_settings = ""
        self.solder_settings = ""

    def make_JSON(self):
        dic_data = {}
        dic_data["Setup"] = self.setup_settings
        dic_data["SolderingProfile"] = self.sol_profile_settings
        dic_data["SelectedSolderingProfile"] = self.sel_sol_profile_settings
        dic_data["NCSettings"] = self.nc_settings
        dic_data["NCHits"] = self.nc_hits
        dic_data["NCTools"] = self.nc_tools
        dic_data["GHome"] = self.g_home
        dic_data["GHeader"] = self.g_header
        dic_data["GSolder"] = self.g_solder
        dic_data["GFooter"] = self.g_footer
        dic_data["GSpool"] = self.g_spool
        dic_data["Panel"] = self.panel_settings
        dic_data["Solder"] = self.solder_settings

        print(dic_data)

    def load_file(self):
        content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()
    def save_file(self):
        self.make_JSON()
        
    def save_as_file(self):
        content = SaveDialog(save=self.save, cancel=self.dismiss_popup)
        self._popup = Popup(title="Save file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def load(self, path, filename):
        
        self.dismiss_popup()

    def save(self, path, filename):
        with open(os.path.join(path, filename), 'w') as stream:
            pass
            #stream.write(self.text_input.text)
        #print(os.path.join(path, filename))
        self.dismiss_popup()

    #### program menu ####
    def import_nc(self):
        content = LoadDialog(load=self.load_nc, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()
    
    def load_nc(self, path, filename):
        self.dismiss_popup()
        self.item_nc_tools.clear()
        self.nc_file_path = filename[0]
        # Read gerber and Excellon files
        data = gerber.read(self.nc_file_path)
        #print(data.statements)
        for tool in iter(data.tools.values()):
            #print(tool)
            self.item_nc_tools.append(str(tool.number) + " : " + str(tool.diameter) + "mm")
        #print(self.item_nc_tools)
        #print(data.tools)
        #print(data.settings)
        #print(data.hits)
        #print(data.report())
        hit_info.clear()
        import math
        xmin = 100000
        xmax = -100000
        ymin = 100000
        ymax = -100000
        for hit in data.hits:
            x, y = hit.position
            radius = hit.tool.diameter/2
            hit_info.append([x*10, y*10, radius*10, hit.tool.number])
            xmin = min(x-radius, xmin)
            xmax = max(x+radius, xmax)
            ymin = min(y-radius, ymin)
            ymax = max(y+radius, ymax)
        
        bound_box["width"] = round((xmax-xmin)*10)
        bound_box["height"] = round((ymax-ymin)*10)
        bound_box["x"] = round(xmin*10)
        bound_box["y"] = round(ymin*10)
        
        self.nc_hits = data.hits
        self.nc_tools = data.tools

        data.to_metric()
        # Rendering context
        ctx = GerberCairoContext(scale=1.0/0.1) # Scale is pixels/mm
        #self.optmize_nc(filename)
        # Create SVG image
        data.render(ctx)
        ctx.dump("temp_origin.png")
        self.cad_img_origin_path = "temp_origin.png"
        self.ids["img_cad_origin"].source = self.cad_img_origin_path
        self.ids["img_cad_origin"].reload()
        # get real image size
        im = pil_image.open('temp_origin.png')
        real_img_size["width"], real_img_size["height"] = im.size
        
        # show image with selected tool(dia)
        self.b_init_dia_tool = True
        self.sel_dia_tool = self.item_nc_tools[0]
        self.write_by_dia(1)
        self.ids["img_cad_origin"].deselect_drill()
    def select_profile(self):
        
        self.items_soldering_profile.clear()
        with open('solderingprofile.json', 'r') as f:
            profile_data = json.load(f)
        
        temp_soldering_profile = []
        for i in range(len(profile_data["SolderingProfile"])):
            if self.sel_soldering_profile == profile_data["SolderingProfile"][i]["Id"]:
                dic_solder = {'text':profile_data["SolderingProfile"][i]["Id"], 'is_selected': True}
                self.b_init_soldering = False
            else:
                dic_solder = {'text':profile_data["SolderingProfile"][i]["Id"], 'is_selected': False}
            temp_soldering_profile.append(dic_solder)
            
            self.items_soldering_profile.append(profile_data["SolderingProfile"][i])
        
        content = ListPopup()
        args_converter = lambda row_index, rec: {'text': rec['text'], 'is_selected': rec['is_selected'], 'size_hint_y': None, 'height': 50}
        list_adapter = ListAdapter(data=temp_soldering_profile, args_converter=args_converter, propagate_selection_to_data=True, cls=ListItemButton, selection_mode='single', allow_empty_selection=False)
        list_view = ListView(adapter=list_adapter)
        
        content.ids.profile_list.add_widget(list_view)
        
        list_view.adapter.bind(on_selection_change=self.selected_profile)
        
        
        self._popup = Popup(title="Select soldering profile", content=content, size_hint=(0.5, 0.6))
        self._popup.open()

    def selected_profile(self, adapter):
        if self.b_init_soldering:
            self.sel_soldering_profile = adapter.selection[0].text
            self.sel_sol_profile_settings = self.get_profile(self.sel_soldering_profile)
            self.ids.lbl_solder_status.text = self.sel_soldering_profile + " / " + self.sel_dia_tool
            self.dismiss_popup()
        else:
            self.b_init_soldering = True
    def get_profile(self, Id):
        for temp in self.sol_profile_settings["SolderingProfile"]:
            if temp["Id"] == Id:
                return temp
    def select_by_dia(self):

        if len(self.item_nc_tools) < 1:
            return
        temp_tools = []
        for tool in self.item_nc_tools:
            if self.sel_dia_tool == tool:
                dic_temp = {'text': tool, 'is_selected': True}
                self.b_init_dia_tool = False
            else:
                dic_temp = {'text': tool, 'is_selected': False}
            temp_tools.append(dic_temp)

        content = ListPopup()
        args_converter = lambda row_index, rec: {'text': rec['text'], 'is_selected': rec['is_selected'], 'size_hint_y': None, 'height': 40}
        list_adapter = ListAdapter(data=temp_tools, args_converter=args_converter, propagate_selection_to_data=True, cls=ListItemButton, selection_mode='single', allow_empty_selection=False)
        list_view = ListView(adapter=list_adapter)
        
        content.ids.profile_list.add_widget(list_view)
        list_view.adapter.bind(on_selection_change=self.selected_tools)
        
        self._popup = Popup(title="Select soldering pad by tools", content=content, size_hint=(0.5, 0.7))
        self._popup.open()
    
    def selected_tools(self, adapter):
        if self.b_init_dia_tool:
            #self.ids.lbl_solder_status.text = adapter.selection[0].text
            self.sel_dia_tool = adapter.selection[0].text
            self.ids.lbl_solder_status.text = self.sel_soldering_profile + " / " + self.sel_dia_tool
            self.dismiss_popup()
            self.write_by_dia(int(self.sel_dia_tool.split(" : ")[0]))
        else:
            self.b_init_dia_tool = True

    def write_by_dia(self, sel_tool):
        str_00_tool = "T" + '{:02d}'.format(sel_tool)
        str_tool = "T" + str(sel_tool)
        b_start = False
        
        with open(self.nc_file_path, 'rU') as f:
            data = f.read()
        self.sel_tool_path = "sel_dia_excellon.txt"
        with open(self.sel_tool_path, 'w') as wf:
            for line in StringIO(data):
                line_temp = line.strip()
                if line_temp[0] == "T":
                    arr_line_temp = line_temp.split("F")
                    if str_tool == arr_line_temp[0] and len(arr_line_temp)>1:
                        wf.write(line_temp + '\n')
                    elif str_00_tool == line_temp:
                        b_start = True
                        wf.write(line_temp + '\n')
                    else:
                        b_start = False
                elif line_temp[0] in ['X', 'Y']:
                    if b_start:
                        wf.write(line_temp + '\n')
                else:
                    wf.write(line_temp + '\n')
        wf.close()
        data = gerber.read(self.sel_tool_path)
        data.to_metric()
        ctx = GerberCairoContext(scale=1.0/0.1) # Scale is pixels/mm
        data.render(ctx)
        ctx.dump("temp_selected.png")
        self.cad_img_sel_path = "temp_selected.png"
        self.ids["img_cad_selected"].source = self.cad_img_sel_path
        self.ids["img_cad_selected"].reload()
    def select_by_view(self):
        sel_hit_info.sort(key=self.take_tool_num)
        
        with open(self.nc_file_path, 'rU') as f:
            data = f.read()
        with open("aaa.txt", 'w') as wf:
            pre_x, pre_y = "", ""
            for line in StringIO(data):
                line_temp = line.strip()
                if line_temp[0] == "T":
                    arr_line_temp = line_temp.split("F")
                    previous_tool = ""
                    for sel_hit in sel_hit_info:
                        x, y, dia, sel_tool = sel_hit
                        if sel_tool != previous_tool:
                            str_00_tool = "T" + '{:02d}'.format(sel_tool)
                            str_tool = "T" + str(sel_tool)
                            if str_tool == arr_line_temp[0] and len(arr_line_temp)>1:
                                wf.write(line_temp + '\n')
                            elif str_00_tool == line_temp:
                                wf.write(line_temp + '\n')

                        previous_tool = sel_tool
                elif line_temp[0] in ['X', 'Y']:
                    arr_temp = line_temp.split("Y")
                    if len(arr_temp)==1:
                        cur_y = pre_y
                        cur_x = arr_temp[0]
                    else: 
                        if arr_temp[0] == '':
                            cur_x = pre_x
                            cur_y = arr_temp[1]
                        else:
                            cur_x = arr_temp[0]
                            cur_y = arr_temp[1]
                    
                    for sel_hit in sel_hit_info:
                        x, y, dia, sel_tool = sel_hit
                        x = int(x*1000000)
                        y = int(y*1000000)
                        str_x = str(x).replace(".","").replace("0","")
                        str_y = str(y).replace(".","").replace("0","")
                        temp_cur_x = str(int(cur_x.replace("X", ""))*1000000).replace("0","")
                        temp_cur_y = str(int(cur_y)*1000000).replace("0","")
                        
                        if temp_cur_x == str_x and temp_cur_y == str_y:
                            wf.write(cur_x + "Y" + cur_y + '\n')
                            #wf.write(line_temp + '\n')

                    pre_x = cur_x
                    pre_y = cur_y
                else:
                    wf.write(line_temp + '\n')
        wf.close()
        data = gerber.read("aaa.txt")
        data.to_metric()
        ctx = GerberCairoContext(scale=1.0/0.1) # Scale is pixels/mm
        data.render(ctx)
        ctx.dump("temp_selected.png")
        self.cad_img_sel_path = "temp_selected.png"
        self.ids["img_cad_selected"].source = self.cad_img_sel_path
        self.ids["img_cad_selected"].reload()
        
        pass
    def take_tool_num(self, elem):
        return elem[3]
    def deselect_by_view(self):
        self.ids["img_cad_origin"].deselect_drill()
    def optmize_nc(self):
        if self.sel_tool_path == "":
            return
        # Read the excellon file
        f = gerber.read(self.sel_tool_path)

        positions   = {}
        tools   = {}
        hit_counts = f.hit_count()
        oldpath = sum(f.path_length().values())

        #print(f.tools)
        #print(f.settings)
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
    #### Connect menu
    def set_printer(self):
        content = EditPopup(save=self.save_printer_port, cancel=self.dismiss_popup)
        content.ids["text_port"].text = self.printer_port
        self._popup = Popup(title="Select Printer port", content=content,
                            size_hint=(0.5, 0.4))
        self._popup.open()
    def save_printer_port(self, txt_port):
        print(txt_port)
        self.dismiss_popup()
        pass

    def set_camera(self):
        content = EditPopup(save=self.save_camera_port, cancel=self.dismiss_popup)
        content.ids["text_port"].text = self.cam_port
        self._popup = Popup(title="Select Camera port", content=content,
                            size_hint=(0.5, 0.4))
        self._popup.open()
    def save_camera_port(self, txt_port):
        print(txt_port)
        self.dismiss_popup()
        pass
    """
    def on_touch_down(self, touch):
        if not self.ids.img_cad_origin.collide_point(*touch.pos):
            return False
        print(touch)
    """
    def dismiss_popup(self):
        self._popup.dismiss()

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
    