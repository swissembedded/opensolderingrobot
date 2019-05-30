
############ Susanna edited #########

import time
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.screenmanager import ScreenManager, Screen
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
from kivy.graphics.texture import Texture
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
# for camera view
import cv2
from videocaptureasync import VideoCaptureAsync

import json
from PIL import Image as pil_image
try:
    from cStringIO import StringIO
except(ImportError):
    from io import StringIO
#to send a file of gcode to the printer
from printrun.printcore import printcore
from printrun import gcoder
# to transform g-code 
from numpy import (array, dot, arccos, clip, subtract, arcsin, arccos)
from numpy.linalg import norm

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
sel_draw_hit_info = []
sel_last_hit_info = {"last":"","first":"","second":""}

def assure_path_exists(path):
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)
assure_path_exists("temp/")
class TouchImage(Image):

    def on_touch_down(self, touch):
        ### mouse down event
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
                        temp = (pos_x, pos_y, dia)
                        if temp in sel_draw_hit_info:
                            sel_draw_hit_info.remove(temp)
                        else:
                            sel_draw_hit_info.append(temp)
                        
                        sel_last_hit_info["last"] = sel_draw_hit_info[-1]
                        self.draw_selected_drill()
                        
                        
            except:
                return True
            return True
        return super(TouchImage, self).on_touch_down(touch)
    def draw_selected_drill(self):
        ### draw all selected drills
        self.canvas.after.clear()
        with self.canvas.after:

            for (pos_x, pos_y, dia) in sel_draw_hit_info:
                x = pos_x - dia
                y = pos_y - dia
                Color(255/255, 0/255, 0/255)
                Ellipse(pos=(x, y), size=(2*dia, 2*dia))
        if sel_last_hit_info["first"] != "":
            pos_x, pos_y, dia = sel_last_hit_info["first"]
            with self.canvas.after:
                x = pos_x - dia
                y = pos_y - dia
                Color(0/255, 0/255, 255/255)
                Ellipse(pos=(x, y), size=(2*dia, 2*dia))
        if sel_last_hit_info["second"] != "":
            pos_x, pos_y, dia = sel_last_hit_info["second"]
            with self.canvas.after:
                x = pos_x - dia
                y = pos_y - dia
                Color(0/255, 255/255, 0/255)
                Ellipse(pos=(x, y), size=(2*dia, 2*dia))
            
    def get_dia_true(self, pos, ratio, x_start, y_start):
        ### get drill hit on current mouse position, 
        ### pos => mouse point, ratio => real image/ nc drills coord, x_start, y_start => computed nc drill coords.
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
                
                temp = (x/10, y/10, radius*2/10, tool_num)
                if temp in sel_hit_info:
                    sel_hit_info.remove(temp)
                else:
                    sel_hit_info.append(temp)
                return True, radius*ratio, (pos_x, pos_y)
        return False, 0, (0, 0)
    def deselect_drill(self):
        self.canvas.after.clear()
        sel_draw_hit_info.clear()
        sel_hit_info.clear()
        sel_last_hit_info["first"]= ""
        sel_last_hit_info["second"] = ""
    

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
class ControlPopup(BoxLayout):
    controlXYZ = ObjectProperty(None)
    goXYZ = ObjectProperty(None)
    saveXYZ = ObjectProperty(None)
    cancel = ObjectProperty(None)
class ErrorDialog(Popup):
    def __init__(self, obj, **kwargs):
        super(ErrorDialog, self).__init__(**kwargs)
        self.obj = obj
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
        self.panel_num = 1
        self.cur_panel_num = 1

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
        self.g_test = ""
        self.g_go = ""
        self.reference_1 = ""
        self.reference_2 = ""
        self.reference_printer = {"1":[(0.0,0.0,0.0)], "2":[(0.0,0.0,0.0)]}
        self.nc_file_data = ""
        self.nc_selected_file_data = ""
        self.project_file_path = ""
        #### port settings 
        self.cam_port = ""
        self.printer_port = ""

        #### soldering settings
        self.b_start_soldering = False
        self.b_started = False
        self.b_test_started = False
        
        #### camera and printer object
        self.print = None
        self.capture = None
        
        self.status_cam = ""
        self.status_printer = ""
        self.TravelZ = 0
        self.ApproxX = 0
        self.ApproxY = 0
        self.ApproxZ = 0
        self.SolderX = 0
        self.SolderY = 0
        self.SolderZ = 0
        self.Heatup = 0
        self.Melting = 0
        self.TravelX = 0
        self.TravelY = 0
        self.CoordX = 0
        self.CoordY = 0
        self.CoordZ = 0

        Clock.schedule_interval(self.init_gui, 0.2)
        Clock.schedule_interval(self.show_status, 0.03)
    def init_gui(self, dt):
        self.new_file()
        Clock.unschedule(self.init_gui) 
        Clock.schedule_interval(self.cam_update, 0.03) 
    def cam_update(self, dt):
        try:
            _, frame = self.capture.read()
            buf1 = cv2.flip(frame, 0)
            buf = buf1.tostring()
            texture1 = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
            texture1.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.ids['img_cam'].texture = texture1
        except Exception as e:
            pass  
    #### File menu
    def exit_app(self):
        self.camera_disconnect()
        self.printer_disconnect()
        App.get_running_app().stop()
    def new_file(self):
        ## File menu / New Project
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

        self.TravelX = self.setup_settings["TravelX"]
        self.TravelY = self.setup_settings["TravelY"]
        self.TravelZ = self.setup_settings["TravelZ"]

        with open('solderingprofile.json', 'r') as f:
            self.sol_profile_settings = json.load(f)
        
        self.sel_soldering_profile = self.sol_profile_settings["SolderingProfile"][0]["Id"]
        self.sel_sol_profile_settings = self.sol_profile_settings["SolderingProfile"][0]

        with open('excellon.json', 'r') as f:
            self.nc_settings = json.load(f)
        self.nc_hits = ""
        self.nc_tools = ""

        with open("printerhome.txt", 'r') as f:
            self.g_home = f.read()
        with open("printerheader.txt", 'r') as f:
            self.g_header = f.read()
        with open("printerfooter.txt", 'r') as f:
            self.g_test = f.read()
        with open("printersoldertest.txt", 'r') as f:
            self.g_footer = f.read()
        with open("printersolder.txt", 'r') as f:
            self.g_solder = f.read()
        with open("printergo.txt", 'r') as f:
            self.g_go = f.read()

        self.reference_1 = ""
        self.reference_2 = ""

        self.nc_file_data = ""
        self.nc_selected_file_data = ""

        self.project_file_path = ""
        
        self.ids["img_cad_origin"].deselect_drill()
        try:
            self.camera_disconnect()
            self.camera_connect()
        except Exception as e:
            print(e, "cam start")
            pass
        
    def make_JSON(self):
        ### make for saving project file
        dic_data = {}
        dic_data["Setup"] = self.setup_settings
        dic_data["SolderingProfile"] = self.sol_profile_settings
        dic_data["SelectedSolderingProfile"] = self.sel_sol_profile_settings
        dic_data["NCSettings"] = self.nc_settings
        
        dic_data["GHome"] = self.g_home
        dic_data["GHeader"] = self.g_header
        dic_data["GSolder"] = self.g_solder
        dic_data["GFooter"] = self.g_footer
        dic_data["GTester"] = self.g_test
        dic_data["GGo"] = self.g_go
        
        ### 
        with open(self.nc_file_path, 'r') as f:
            self.nc_file_data = f.read()

        with open(self.sel_tool_path, 'r') as f:
            self.nc_selected_file_data = f.read()    
        
        dic_data["NCFile"] = self.nc_file_data
        dic_data["SelectedFile"] = self.nc_selected_file_data
        dic_data["Panel_num"] = self.panel_num
        dic_data["Panel_references"] = self.reference_printer
        dic_data["NCReference1"] = self.reference_1
        dic_data["NCReference2"] = self.reference_2
        dic_data["Reference1_point"] = sel_last_hit_info["first"]
        dic_data["Reference2_point"] = sel_last_hit_info["second"]
        dic_data["SelectedDrills_draw"] =sel_draw_hit_info
        dic_data["SelectedDrills"] = sel_hit_info
        return dic_data

    def load_file(self):
        ### File Menu / Load project
        content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()
    def save_file(self):
        ### File Menu / Save Project
        if self.project_file_path == "":
            self.save_as_file()
        else:
            dic_data1 = self.make_JSON()
            with open(self.project_file_path, 'w') as fp:
                json.dump(dic_data1, fp, indent=4, sort_keys=True)
        
    def save_as_file(self):
        ### File Menu / Save as Project
        content = SaveDialog(save=self.save, cancel=self.dismiss_popup)
        self._popup = Popup(title="Save file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def load(self, path, filename):
        ### click load button of Loading Dialog
        ### load all info from pre saved project file
        try:
            ### if proper project file
            with open(filename[0]) as json_data:
                dic_data = json.load(json_data) 
                self.project_file_path = filename[0]
        except:
            ### if not proper project file
            self.dismiss_popup()
            return
        self.setup_settings = dic_data["Setup"]
        self.sol_profile_settings = dic_data["SolderingProfile"]
        self.sel_sol_profile_settings = dic_data["SelectedSolderingProfile"]
        self.nc_settings = dic_data["NCSettings"]
        
        self.g_home = dic_data["GHome"]
        self.g_header = dic_data["GHeader"] 
        self.g_solder = dic_data["GSolder"] 
        self.g_footer = dic_data["GFooter"]
        self.g_test = dic_data["GTester"]
        self.g_go = dic_data["GGo"] 
        self.nc_file_data = dic_data["NCFile"]
        self.nc_selected_file_data = dic_data["SelectedFile"]
        self.panel_num = dic_data["Panel_num"]
        self.reference_printer = dic_data["Panel_references"]
        self.reference_1 = dic_data["NCReference1"] 
        self.reference_2 = dic_data["NCReference2"]
        

        self.nc_file_path = "./temp/nc_origin_file.txt"
        self.sel_tool_path = "./temp/sel_dia_excellon.txt"

        with open(self.nc_file_path, 'w') as wf:
            wf.write(self.nc_file_data)
        wf.close()
        
        self.load_nc('', [self.nc_file_path])
        
        with open(self.sel_tool_path, 'w') as wf:
            wf.write(self.nc_selected_file_data)
        wf.close()

        self.refresh_selected_view()

        ### draw reference point 1 and 2
        if dic_data["Reference1_point"] != "":
            sel_last_hit_info["first"] = dic_data["Reference1_point"]
            sel_last_hit_info["last"] = sel_last_hit_info["first"]
            
        if dic_data["Reference2_point"] != "":
            sel_last_hit_info["second"] = dic_data["Reference2_point"]
            sel_last_hit_info["last"] = sel_last_hit_info["second"]
            
        
        sel_draw_hit_info = dic_data["SelectedDrills_draw"]
        sel_hit_info = dic_data["SelectedDrills"]
        self.ids["img_cad_origin"].draw_selected_drill()
        self.dismiss_popup()

    def save(self, path, filename):
        ### after click Save button of Save Dialog
        if not ".json" in filename:
            filename = filename + ".json"
        with open(os.path.join(path, filename), 'w') as stream:
            dic_data1 = self.make_JSON()
            json.dump(dic_data1, stream, indent=4, sort_keys=True)

            self.project_file_path = os.path.join(path, filename)
        self.dismiss_popup()

    #### program menu ####
    def import_nc(self):
        ### Program menu / import NC drills
        content = LoadDialog(load=self.load_nc, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()
    
    def load_nc(self, path, filename):
        ### after click load button of Loading button
        
        self.dismiss_popup()
        self.item_nc_tools.clear()
        self.nc_file_path = filename[0]
         
        try:
            # Read gerber and Excellon files
            data = gerber.read(self.nc_file_path)
            for tool in iter(data.tools.values()):
                self.item_nc_tools.append(str(tool.number) + " : " + str(tool.diameter) + "mm")
            hit_info.clear()
            
            ### get relation between appeared Image Pixels and PCB coordinate
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
            data.render(ctx)
        except Exception as e:
            print(e, "Load NC Drills")
            popup = ErrorDialog(self)
            popup.open()
            return
        
        ctx.dump("./temp/temp_origin.png")
        self.cad_img_origin_path = "./temp/temp_origin.png"
        self.ids["img_cad_origin"].source = self.cad_img_origin_path
        self.ids["img_cad_origin"].reload()
        # get real image size
        im = pil_image.open('./temp/temp_origin.png')
        real_img_size["width"], real_img_size["height"] = im.size
        
        # show image with selected tool(dia)
        self.b_init_dia_tool = True
        self.sel_dia_tool = self.item_nc_tools[0]
        self.write_by_dia(1)
        self.ids["img_cad_origin"].deselect_drill()
    def select_profile(self):
        ### Program menu / Select Soldering Profile
        self.items_soldering_profile.clear()
                
        temp_soldering_profile = []
        for i in range(len(self.sol_profile_settings["SolderingProfile"])):
            if self.sel_soldering_profile == self.sol_profile_settings["SolderingProfile"][i]["Id"]:
                dic_solder = {'text':self.sol_profile_settings["SolderingProfile"][i]["Id"], 'is_selected': True}
                self.b_init_soldering = False
            else:
                dic_solder = {'text':self.sol_profile_settings["SolderingProfile"][i]["Id"], 'is_selected': False}
            temp_soldering_profile.append(dic_solder)
            
            self.items_soldering_profile.append(self.sol_profile_settings["SolderingProfile"][i])
        
        content = ListPopup()
        args_converter = lambda row_index, rec: {'text': rec['text'], 'is_selected': rec['is_selected'], 'size_hint_y': None, 'height': 50}
        list_adapter = ListAdapter(data=temp_soldering_profile, args_converter=args_converter, propagate_selection_to_data=True, cls=ListItemButton, selection_mode='single', allow_empty_selection=False)
        list_view = ListView(adapter=list_adapter)
        
        content.ids.profile_list.add_widget(list_view)
        
        list_view.adapter.bind(on_selection_change=self.selected_profile)
        
        
        self._popup = Popup(title="Select soldering profile", content=content, size_hint=(0.5, 0.6))
        self._popup.open()

    def selected_profile(self, adapter):
        ### select profile on soldering profile list
        if self.b_init_soldering:
            self.sel_soldering_profile = adapter.selection[0].text
            self.sel_sol_profile_settings = self.get_profile(self.sel_soldering_profile)
            self.ids.lbl_solder_status.text = self.sel_soldering_profile + " / " + self.sel_dia_tool
            self.dismiss_popup()
        else:
            self.b_init_soldering = True
    def get_profile(self, Id):
        ### get selected soldering profile json data from id
        for temp in self.sol_profile_settings["SolderingProfile"]:
            if temp["Id"] == Id:
                return temp
    def select_by_dia(self):
        ### Program Menu / Select soldering pad by diameter
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
        ### select tool on tools' list
        if self.b_init_dia_tool:
            self.sel_dia_tool = adapter.selection[0].text
            self.ids.lbl_solder_status.text = self.sel_soldering_profile + " / " + self.sel_dia_tool
            self.dismiss_popup()
            self.write_by_dia(int(self.sel_dia_tool.split(" : ")[0]))
        else:
            self.b_init_dia_tool = True

    def write_by_dia(self, sel_tool):
        ### write nc drills selected by dia to file
        str_00_tool = "T" + '{:02d}'.format(sel_tool)
        str_tool = "T" + str(sel_tool)
        b_start = False
        
        with open(self.nc_file_path, 'r') as f:
            data = f.read()
        self.sel_tool_path = "./temp/sel_dia_excellon.txt"
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
        self.refresh_selected_view()
    def select_by_view(self):
        ### Program menu / Select Soldering pads by View
        if len(sel_hit_info) < 1:
            return
        sel_hit_info.sort(key=self.take_tool_num)
        
        with open(self.nc_file_path, 'r') as f:
            data = f.read()
        self.sel_tool_path = "./temp/sel_dia_excellon.txt"
        with open(self.sel_tool_path, 'w') as wf:
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
        self.refresh_selected_view()
    

    def refresh_selected_view(self):
        ### refresh selected cad view 
        data = gerber.read(self.sel_tool_path)
        data.to_metric()
        ctx = GerberCairoContext(scale=1.0/0.1) # Scale is pixels/mm
        data.render(ctx)
        ctx.dump("./temp/temp_selected.png")
        self.cad_img_sel_path = "./temp/temp_selected.png"
        self.ids["img_cad_selected"].source = self.cad_img_sel_path
        self.ids["img_cad_selected"].reload()    
    def take_tool_num(self, elem):
        return elem[3]
    def deselect_by_view(self):
        ### Program Menu / Deselect by view
        self.ids["img_cad_origin"].deselect_drill()
        self.ids["img_cad_selected"].source = ""
    def set_reference1(self):
        ### Program Menu / Set Reference point 1
        if len(sel_hit_info) < 1:
            return
        self.reference_1 = sel_hit_info[len(sel_hit_info)-1]
        del sel_hit_info[-1]
        del sel_draw_hit_info[-1]
        sel_last_hit_info["first"] = sel_last_hit_info["last"]
        self.ids["img_cad_origin"].draw_selected_drill()
    def set_reference2(self):
        ### Program Menu /  Set Reference Point 2
        if len(sel_hit_info) < 1:
            return
        self.reference_2 = sel_hit_info[len(sel_hit_info)-1]
        del sel_hit_info[-1]
        del sel_draw_hit_info[-1]
        sel_last_hit_info["second"] = sel_last_hit_info["last"]
        self.ids["img_cad_origin"].draw_selected_drill()
    def optmize_nc(self):
        ### Program Menu / Optmize NC drills
        if self.sel_tool_path == "":
            return
        # Read the excellon file
        f = gerber.read(self.sel_tool_path)

        positions   = {}
        tools   = {}
        hit_counts = f.hit_count()
        oldpath = sum(f.path_length().values())

        for hit in f.hits:
            tool_num = hit.tool.number
            if tool_num not in positions.keys():
                positions[tool_num]   = []
            positions[tool_num].append(hit.position)
            print(hit.position)

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
        f.filename = self.sel_tool_path
        f.write()
        
        # Print drill report
        print(f.report())
        print('Original path length:  %1.4f' % oldpath)
        print('Optimized path length: %1.4f' % sum(f.path_length().values()))

    ##### panel menu
    def set_num_panel(self):
        content = EditPopup(save=self.save_panel_num, cancel=self.dismiss_popup)
        content.ids["btn_connect"].text = "Save"
        content.ids["text_port"].text = str(self.panel_num)
        self._popup = Popup(title="Select panel num", content=content,
                            size_hint=(0.5, 0.4))
        self._popup.open()
    def save_panel_num(self, txt_port):
        self.panel_num  = int(txt_port)
        self.reference_printer["1"] = [(0.0,0.0,0.0)]*self.panel_num
        self.reference_printer["2"] = [(0.0,0.0,0.0)]*self.panel_num
        
        self.dismiss_popup()

    def set_reference_panel(self):
        
        self.ids["tab_panel"].switch_to(self.ids["tab_panel"].tab_list[0])
        self.content = ControlPopup(controlXYZ=self.control_XYZ, goXYZ=self.go_XYZ, saveXYZ=self.save_XYZ, cancel=self.dismiss_popup)
        self.content.ids["cur_X"].text = str(self.TravelX)
        self.content.ids["cur_Y"].text = str(self.TravelY)
        self.content.ids["cur_Z"].text = str(self.TravelZ)
        self.content.ids["cur_panel"].text = str(self.cur_panel_num)

        if self.printer_connect() is False:
            return
        
        gcode = self.send_gcode_from_template(self.g_home)
        gcode1 = gcoder.LightGCode(gcode)
        self.print.startprint(gcode1)
            
        self._popup = Popup(title="Set reference point", content=self.content,
                            size_hint=(0.4, 0.4))
        self._popup.pos_hint={"center_x": .8, "center_y": .8}
        self._popup.open()
    def control_XYZ(self, axis, value):
        ### click any button on dialpad
        if axis == "X":
            self.CoordX += float(value)
        elif axis == "Y":
            self.CoordY += float(value)
        elif axis == "Z":
            if value == 0:
                self.CoordZ = self.TravelZ
            else:
                self.CoordZ += float(value)
        else:
            self.CoordX = self.TravelX
            self.CoordY = self.TravelY

        self.CoordX = round(self.CoordX, 5)
        self.CoordY = round(self.CoordY, 5)
        self.CoordZ = round(self.CoordZ, 5)
        
        self.content.ids["cur_X"].text = str(self.CoordX)
        self.content.ids["cur_Y"].text = str(self.CoordY)
        self.content.ids["cur_Z"].text = str(self.CoordZ)
        #### go to printer point (gcode sent)
        temp_gcode = self.send_gcode_from_template(self.g_go)
        print("#### control dialpad ===>", temp_gcode)
        
    def go_XYZ(self, next_x, next_y, next_z):
        ### click go button on dialpad
        self.CoordX = round(float(next_x), 5)
        self.CoordY = round(float(next_y), 5)
        self.CoordZ = round(float(next_z), 5)
        #### go to printer point (gcode sent)
        temp_gcode = self.send_gcode_from_template(self.g_go)
        print("#### control dialpad go! ===>", temp_gcode)
        
    def save_XYZ(self, cur_panel, cur_x, cur_y, cur_z, refer):
        ### click Set 1 and Set 2 button refer = 1 ==> Set 1, refer = 2 ==> Set 2
        try:
            if int(cur_panel) <= self.panel_num and int(cur_panel)>=1:
                self.cur_panel_num = int(cur_panel)
                if refer == 1:
                    self.reference_printer["1"][int(cur_panel)-1] = (float(cur_x), float(cur_y), float(cur_z))
                else:
                    self.reference_printer["2"][int(cur_panel)-1] = (float(cur_x), float(cur_y), float(cur_z))
            else:
                print("please enter 1~" + str(self.panel_num))
        except:
            print("please enter correct current panel")
        
    #### Connect menu
    def set_printer(self):
        ### Connect Menu /  Connect Printer
        content = EditPopup(save=self.save_printer_port, cancel=self.dismiss_popup)
        content.ids["text_port"].text = self.printer_port
        self._popup = Popup(title="Select Printer port", content=content,
                            size_hint=(0.5, 0.4))
        self._popup.open()
    def save_printer_port(self, txt_port):
        self.printer_post = txt_port
        self.dismiss_popup()
        
    def set_camera(self):
        content = EditPopup(save=self.save_camera_port, cancel=self.dismiss_popup)
        content.ids["text_port"].text = self.cam_port
        self._popup = Popup(title="Select Camera port", content=content,
                            size_hint=(0.5, 0.4))
        self._popup.open()
    def save_camera_port(self, txt_port):
        self.cam_port = txt_port
        try:
            self.camera_disconnect()
            self.camera_connect()
        except  Exception as e:
            print(e," save cam port")
            pass
        self.dismiss_popup()
    def get_printer_point(self, point, radians, scale, origin=(0, 0), translation=(0,0)):
        ### get printer point from nc drill coordinates
        x, y = point
        ox, oy = origin
        tx, ty = translation

        qx = tx + (math.cos(radians) * (x - ox) + math.sin(radians) * (y - oy))*scale
        qy = ty + (-math.sin(radians) * (x - ox) + math.cos(radians) * (y - oy))*scale

        return qx, qy    
    def get_soldering_setting(self):
        ### get selected soldering profile
        
        self.SolderLength = self.sel_sol_profile_settings["SolderLength"]
        self.Melting = self.sel_sol_profile_settings["Melting"]
        self.Heatup = self.sel_sol_profile_settings["Heatup"]
        
        self.SolderOffsetX = self.sel_sol_profile_settings["SolderOffsetX"]
        self.SolderOffsetY = self.sel_sol_profile_settings["SolderOffsetY"]
        self.SolderOffsetZ= self.sel_sol_profile_settings["SolderOffsetZ"]

        self.ApproxOffsetX = self.sel_sol_profile_settings["ApproxOffsetX"]
        self.ApproxOffsetY = self.sel_sol_profile_settings["ApproxOffsetY"]
        self.ApproxOffsetZ = self.sel_sol_profile_settings["ApproxOffsetZ"]
    def start_soldering(self):
        if self.ids["btn_start"].text == "start soldering" and self.b_test_started is False:
            if self.reference_1 != "" and self.reference_2 != "":
                if self.printer_connect() is False:
                    return
                
                gcode = self.send_gcode_from_template(self.g_header)
                # or pass in your own array of gcode lines instead of reading from a file
                gcode1 = gcoder.LightGCode(gcode)
                self.print.startprint(gcode1) # this will start a print
                self.b_started = True
                self.ids["btn_start"].text = "pause soldering"
                self.get_soldering_setting()
                gcode.extend(self.panel_soldering(self.g_solder))
                gcode.extend(self.send_gcode_from_template(self.g_footer))     
                
                with open("./temp/gcode.txt", 'w') as wf:
                    print(gcode)
                    for temp in gcode:
                        wf.write(temp+"\n")
                wf.close()
                #print(gcode)
                
        else:
            if self.b_start_soldering and self.b_started:
                
                if self.print is not None:
                    self.b_start_soldering = False
                    self.ids["btn_start"].text = "pause soldering"
                    self.print.resume()
            elif self.b_start_soldering == False and self.b_started:
                
                if self.print is not None:
                    self.print.send_now("M105") # this will send M105 immediately, ahead of the rest of the print
                    self.print.pause() # use these to pause/resume the current print
                    self.b_start_soldering = True
                    self.ids["btn_start"].text = "resume soldering"
                    #If you need to interact with the printer:
    def panel_soldering(self, template):
        ######## for each panel soldering ; template == self.g_solder ==> soldering, template ==self.g_test ==> testing
        gcode = []
        for k in range(len(self.reference_printer["1"])):
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
        return gcode       
    def stop_soldering(self):
        self.printer_disconnect()
        
    def test_soldering(self):
        if self.ids["btn_test"].text == "test soldering" and self.b_started is False:
            if self.reference_1 != "" and self.reference_2 != "":
                if self.printer_connect() is False:
                    return

                gcode = self.send_gcode_from_template(self.g_header)
                # or pass in your own array of gcode lines instead of reading from a file
                gcode1 = gcoder.LightGCode(gcode)
                self.print.startprint(gcode1) # this will start a print
                self.b_test_started = True
                self.ids["btn_test"].text = "pause soldering"
                self.get_soldering_setting()
                gcode.extend(self.panel_soldering(self.g_test))
                gcode.extend(self.send_gcode_from_template(self.g_footer))     
                
                with open("./temp/gcode.txt", 'w') as wf:
                    print(gcode)
                    for temp in gcode:
                        wf.write(temp+"\n")
                wf.close()
                #print(gcode)
                
        else:
            if self.b_start_soldering and self.b_test_started:
                if self.print is not None:
                    self.b_start_soldering = False
                    self.ids["btn_test"].text = "pause soldering"
                    self.print.resume()
            elif self.b_start_soldering == False and self.b_test_started:
                if self.print is not None:
                    self.b_start_soldering = True
                    self.ids["btn_test"].text = "resume soldering"
                    #If you need to interact with the printer:
                    self.print.send_now("M105") # this will send M105 immediately, ahead of the rest of the print
                    self.print.pause() # use these to pause/resume the current print  

    def dismiss_popup(self):
        self.printer_disconnect()
        self._popup.dismiss()
    def camera_connect(self):
        ### connect camera
        self.capture = VideoCaptureAsync(self.cam_port)
        self.capture.start()
        self.status_cam = "Camera connected"
        self.ids["lbl_cad_cam"].text = self.status_printer + "  " + self.status_cam
    def camera_disconnect(self):
        if self.capture is not None:
            self.capture.stop()
            self.capture = None
    def printer_connect(self):
        if self.print is None:
            self.print = printcore(self.printer_port, 115200) # or p.printcore('COM3',115200) on Windows
            waiting_counter = 1
            ### not printer online, wait , after 1 sec, connect failed
            while not self.print.online: 
                self.status_printer = " 3d printer connecting..."
                self.ids["lbl_cad_cam"].text = self.status_printer + "  " + self.status_cam
                time.sleep(0.1)
                waiting_counter +=1
                if waiting_counter > 10:
                    self.print = None
                    self.status_printer = " 3d printer not connected"
                    self.ids["lbl_cad_cam"].text = self.status_printer + "  " + self.status_cam
                    return False
            self.status_printer = " 3d printer connected"
            self.ids["lbl_cad_cam"].text = self.status_printer + "  " + self.status_cam
            return True
    def printer_disconnect(self):
        if self.print is not None:
            self.print.disconnect()
            self.print = None
            self.status_printer = " 3d printer disconnected"
            self.ids["lbl_cad_cam"].text = self.status_printer + "  " + self.status_cam
            self.ids["btn_start"].text = "start soldering"
            self.ids["btn_test"].text = "test soldering"
            self.b_start_soldering = False
            self.b_test_started = False
            self.b_started = False
    def send_gcode_from_template(self, template):
        gcode=[]
        for line in StringIO(template):
            converted_line = line.strip().replace("%TravelZ", str(self.TravelZ))
            converted_line = converted_line.replace("%ApproxX", str(self.ApproxX))
            converted_line = converted_line.replace("%ApproxY", str(self.ApproxY))
            converted_line = converted_line.replace("%ApproxZ", str(self.ApproxZ))
            converted_line = converted_line.replace("%SolderX", str(self.SolderX))
            converted_line = converted_line.replace("%SolderY", str(self.SolderY))
            converted_line = converted_line.replace("%SolderZ", str(self.SolderZ))
            converted_line = converted_line.replace("%Heatup", str(self.Heatup))
            converted_line = converted_line.replace("%Melting", str(self.Melting))
            converted_line = converted_line.replace("%TravelX", str(self.TravelX))
            converted_line = converted_line.replace("%TravelY", str(self.TravelY))
            converted_line = converted_line.replace("%CoordX", str(self.CoordX))
            converted_line = converted_line.replace("%CoordY", str(self.CoordY))
            converted_line = converted_line.replace("%CoordZ", str(self.CoordZ))

            self.print.send(converted_line)
            gcode.append(converted_line)
        return gcode 
    def show_status(self, dt):
        if  self.ids is not "":
            #self.ids["lbl_cad_cam"].text = " Camera connected" 
            if self.print is not None and (self.b_started or self.b_test_started): 
                try:
                    (layer, line) = self.print.mainqueue.idxs(self.print.queueindex)
                    gline = self.print.mainqueue.all_layers[layer][line]
                    #print(gline.raw)
                    self.ids["lbl_solder_status"].text = str(gline.raw)[0:70]#" soldering 1/N pads on panel 2/M"
                    if str(gline.raw) == "G1 X0 Y0 F600 ; end":
                        self.print.disconnect()
                except Exception as e:
                    self.print.disconnect()
                    

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
        self.screen_manage = ScreenManagement()
        return self.screen_manage
    def on_stop(self):
        self.screen_manage.current_screen.camera_disconnect()
        self.screen_manage.current_screen.printer_disconnect()


if __name__ == '__main__':
    Builder.load_file("main.kv")
    MyApp().run()
    cv2.destroyAllWindows()