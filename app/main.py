# Gerber / Excellon handling
# This file is part of the opensoldering project distribution (https://github.com/swissembedded/opensolderingrobot.git).
# Copyright (c) 2019 by Susanna
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

import time
import datetime
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

import data
import excellon
import robotcontrol

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
    def set_cad_view(self, prjdata):
        # make it globally available
        self.project_data=prjdata

    def redraw_cad_view(self):
        ### redraw the cad view
        soldertoolpath=self.project_data['SolderToolpath']
        solderside=self.project_data['SolderSide']
        selectedsolderingprofile=self.project_data['SelectedSolderingProfile']
        posxp, posyp=self.pos
        widthp, heightp = self.size
        xmin, xmax, ymin, ymax = excellon.get_nc_tool_area(soldertoolpath)
        width=xmax-xmin
        height=ymax-ymin

        if width==0 or height==0:
            return

        self.canvas.after.clear()
        with self.canvas.after:
                Color(0/255,0/255,0/255)
                Rectangle(pos=(posxp, posyp), size=(widthp, heightp))
                posxp=posxp+widthp*0.01
                posyp=posyp+heightp*0.01
                widthp*=0.98
                heightp*=0.98
                scale=min(widthp / width, heightp / height)
                for e, elem in enumerate(soldertoolpath):
                    tp=soldertoolpath[e]
                    x=tp['NCPositionX']
                    y=tp['NCPositionY']
                    d=tp['NCDiameter']
                    ref1=tp['PanelRef1']
                    ref2=tp['PanelRef2']
                    profile=tp['SolderingProfile']

                    xp, yp=excellon.get_pixel_position(soldertoolpath,x,y,width*scale,height*scale)
                    if ref1:
                        Color(255/255, 0/255, 0/255)
                    elif ref2:
                        Color(0/255, 0/255, 255/255)
                    elif profile!=-1:
                        if profile==selectedsolderingprofile:
                            Color(128/255, 255/255, 128/255)
                        else:
                            Color(128/255, 128/255, 255/255)
                    else:
                        Color(64/255, 64/255, 64/255)
                    if solderside=="Top":
                        Ellipse(pos=(xp+posxp, yp+posyp), size=(d*scale, d*scale))
                    else:
                        Ellipse(pos=(widthp-xp+posxp, yp+posyp), size=(d*scale, d*scale))

    def on_touch_down(self, touch):
        ### mouse down event
        print(touch.pos, self.pos, self.size)
        #return super(TouchImage, self).on_touch_down(touch)
        soldertoolpath=self.project_data['SolderToolpath']
        solderside=self.project_data['SolderSide']
        selectedsolderingprofile=self.project_data['SelectedSolderingProfile']
        mode=self.project_data['CADMode']
        posxp, posyp=self.pos
        widthp, heightp = self.size
        xmin, xmax, ymin, ymax=excellon.get_nc_tool_area(soldertoolpath)
        width=xmax-xmin
        height=ymax-ymin

        if width==0 or height==0:
            return

        # calculate click position
        posxp=posxp+widthp*0.01
        posyp=posyp+heightp*0.01

        # scaling
        widthp*=0.98
        heightp*=0.98
        scale=min(widthp / width, heightp / height)

        touchxp, touchyp=touch.pos

        if solderside=="Top":
            touchxp=touchxp-posxp
            touchyp=touchyp-posyp
        else:
            touchxp=widthp-touchxp-posxp
            touchyp=touchyp-posyp

        xnc, ync = excellon.get_nc_tool_position(soldertoolpath,touchxp,touchyp,width*scale,height*scale)
        #print("click",ymin,ymin, touchxp, touchyp, xnc, ync)
        # out of image
        if xnc < xmin or xnc > xmax or ync < ymin or ync > ymax:
            return
        # perform action on mode
        if mode=="Select":
            excellon.select_by_position(soldertoolpath, xnc, ync, selectedsolderingprofile)
        elif mode=="Deselect":
            excellon.deselect_by_position(soldertoolpath, xnc, ync)
        elif mode=="Ref1":
            excellon.set_reference_1(soldertoolpath, xnc, xnc)
        elif mode=="Ref2":
            excellon.set_reference_2(soldertoolpath, xnc, xnc)
        self.redraw_cad_view()
        return

class LoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)
class SaveDialog(FloatLayout):
    save = ObjectProperty(None)
    text_input = ObjectProperty(None)
    cancel = ObjectProperty(None)
class ImportDialog(FloatLayout):
    load = ObjectProperty(None)
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

### this is the main screen
class ListScreen(Screen):
    def __init__(self, **kwargs):
        super(ListScreen, self).__init__(**kwargs)
        # run clock
        # TODO
        Clock.schedule_interval(self.init_gui, 0.2)
        #Clock.schedule_interval(self.show_status, 0.03)

    def init_gui(self, dt):
        self.new_file()
        Clock.unschedule(self.init_gui)
        #TODO
        #Clock.schedule_interval(self.cam_update, 0.03)

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


        # init status bar
        # TODO

    def init_project(self):
        # init data
        self.project_file_path = ""
        self.project_data=data.init_project_data()
        self.project_data['CADMode']="None"
        self.ids["img_cad_origin"].set_cad_view(self.project_data)
        self.ids["img_cad_origin"].redraw_cad_view()

        try:
            self.camera_disconnect()
            self.camera_connect()
        except Exception as e:
            print(e, "cam start")
            pass

    def load_file(self):
        ### File Menu / Load project
        content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()
        self.project_data['CADMode']="None"

    def load(self, path, filename):
        ### click load button of Loading Dialog
        ### load all info from pre saved project file
        try:
            ### if proper project file
            self.project_file_path =  filename[0]
            self.project_data=data.read_project_data(self.project_file_path)
            self.ids["img_cad_origin"].redraw_cad_view()
        except:
            ### if not proper project file
            self.dismiss_popup()
            return
        self.dismiss_popup()

    def save_file(self):
        ### File Menu / Save Project
        if self.project_file_path == "":
            self.save_as_file()
        else:
            data.write_project_data(self.project_file_path, self.project_data)

    def save_as_file(self):
        ### File Menu / Save as Project
        content = SaveDialog(save=self.save, cancel=self.dismiss_popup)
        self._popup = Popup(title="Save file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()
        self.project_data['CADMode']="None"

    def save(self, path, filename):
        ### after click Save button of Save Dialog
        self.project_file_path = os.path.join(path, filename)
        print(path, filename, self.project_file_path)
        data.write_project_data(self.project_file_path, self.project_data)
        self.dismiss_popup()


    #### program menu ####
    def import_file(self):
        ### Program menu / import NC drills
        content = ImportDialog(load=self.import_ncdrill, cancel=self.dismiss_popup)
        self._popup = Popup(title="Import file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()
        self.project_data['CADMode']="None"

    def import_ncdrill(self, path, filename):

        ### after click load button of Loading button
        try:
            ### if proper project file
            nc_file_path  = filename[0]
            ncdata=excellon.load_nc_drill(nc_file_path)
            print("ncdata", ncdata)
            # convert tool list for selection
            self.project_data['NCTool']=excellon.convert_to_tools(ncdata)
            # convert soldering tool path
            self.project_data['SolderToolpath']=excellon.convert_to_json(ncdata)
            # redraw
            self.ids["img_cad_origin"].redraw_cad_view()

        except:
            ### if not proper project file
            self.dismiss_popup()
            return

        self.dismiss_popup()


    def select_side(self):
        ### Program menu / Select Soldering Side
        side = [  { "text" : "Top", "is_selected" : self.project_data['SolderSide']=="Top" },
                { "text" : "Bottom", "is_selected" : self.project_data['SolderSide']=="Bottom" }  ]
        self.ignore_first=not side[0]['is_selected']

        content = ListPopup()
        args_converter = lambda row_index, rec: {'text': rec['text'], 'is_selected': rec['is_selected'], 'size_hint_y': None, 'height': 50}
        list_adapter = ListAdapter(data=side, args_converter=args_converter, propagate_selection_to_data=True, cls=ListItemButton, selection_mode='single', allow_empty_selection=False)
        list_view = ListView(adapter=list_adapter)

        content.ids.profile_list.add_widget(list_view)

        list_view.adapter.bind(on_selection_change=self.selected_side)

        self._popup = Popup(title="Select Soldering Side", content=content, size_hint=(0.5, 0.6))
        self._popup.open()
        self.project_data['CADMode']="None"

    def selected_side(self, adapter):
        if self.ignore_first:
            self.ignore_first=False
            return
        self.project_data['SolderSide']=adapter.selection[0].text
        self.dismiss_popup()
        self.ids["img_cad_origin"].redraw_cad_view()

    def select_profile(self):
        ### Program menu / Select Soldering Profile
        profile = excellon.convert_to_solderingprofile(self.project_data)
        if len(profile) < 1:
            return
        self.ignore_first=not profile[0]['is_selected']
        content = ListPopup()
        args_converter = lambda row_index, rec: {'text': rec['text'], 'is_selected': rec['is_selected'], 'size_hint_y': None, 'height': 50}
        list_adapter = ListAdapter(data=profile, args_converter=args_converter, propagate_selection_to_data=True, cls=ListItemButton, selection_mode='single', allow_empty_selection=False)
        list_view = ListView(adapter=list_adapter)

        content.ids.profile_list.add_widget(list_view)

        list_view.adapter.bind(on_selection_change=self.selected_profile)

        self._popup = Popup(title="Select Soldering Profile", content=content, size_hint=(0.5, 0.6))
        self._popup.open()
        self.project_data['CADMode']="None"

    def selected_profile(self, adapter):
        ### select profile on soldering profile list
        if self.ignore_first:
            self.ignore_first=False
            return
        num=excellon.get_solderingprofile_index_by_id(self.project_data['SolderingProfile']['SolderingProfile'], adapter.selection[0].text)
        self.project_data['SelectedSolderingProfile']=num
        self.dismiss_popup()
        self.ids["img_cad_origin"].redraw_cad_view()


    def select_by_dia(self):
        ### Program Menu / Select soldering pad by diameter
        tools=self.project_data['NCTool']
        if len(tools) < 1:
            return
        self.ignore_first=not tools[0]['is_selected']

        content = ListPopup()
        args_converter = lambda row_index, rec: {'text': rec['text'], 'is_selected': rec['is_selected'], 'size_hint_y': None, 'height': 40}
        list_adapter = ListAdapter(data=tools, args_converter=args_converter, propagate_selection_to_data=True, cls=ListItemButton, selection_mode='single', allow_empty_selection=False)
        list_view = ListView(adapter=list_adapter)

        content.ids.profile_list.add_widget(list_view)
        list_view.adapter.bind(on_selection_change=self.selected_tools)

        self._popup = Popup(title="Select Soldering Pad by Tools", content=content, size_hint=(0.5, 0.7))
        self._popup.open()
        self.project_data['CADMode']="None"

    def selected_tools(self, adapter):
        ### select tool on tools' list
        if self.ignore_first:
            self.ignore_first=False
            return
        soldertoolpath=self.project_data['SolderToolpath']
        num=int(adapter.selection[0].text.split(":")[0])
        excellon.select_by_tool(soldertoolpath, num, self.project_data['SelectedSolderingProfile'])
        # redraw
        self.dismiss_popup()
        self.ids["img_cad_origin"].redraw_cad_view()

    def select_by_view(self):
        ### Program menu / Select Soldering pads by View
        self.project_data['CADMode']="Select"

    def deselect_by_view(self):
        ### Program Menu / Deselect by view
        self.project_data['CADMode']="Deselect"

    def set_reference1(self):
        ### Program Menu / Set Reference point 1
        self.project_data['CADMode']="Ref1"

    def set_reference2(self):
        ### Program Menu /  Set Reference Point 2
        self.project_data['CADMode']="Ref2"

    def optmize_nc(self):
        ### Program Menu / Optmize NC drills
        soldertoolpath=self.project_data['SolderToolpath']
        excellon.optimize_soldertoolpath(soldertoolpath)

    ##### panel menu
    def set_num_panel(self):
        num=excellon.get_num_panel(self.project_data['Panel'])
        content = EditPopup(save=self.save_panel_num, cancel=self.dismiss_popup)
        content.ids["btn_connect"].text = "Save"
        content.ids["text_port"].text = str(num)
        self._popup = Popup(title="Select panel num", content=content,
                            size_hint=(0.5, 0.4))
        self._popup.open()
        self.project_data['CADMode']="None"

    def save_panel_num(self, txt_port):
        # set num of panels
        num  = int(txt_port)
        excellon.set_num_panel(self.project_data['Panel'], num)
        self.dismiss_popup()

    def set_reference_panel(self):
        #  show dialpad

        self.ids["tab_panel"].switch_to(self.ids["tab_panel"].tab_list[0])
        self.content = ControlPopup(controlXYZ=self.control_XYZ, goXYZ=self.go_XYZ, saveXYZ=self.save_XYZ, cancel=self.dismiss_popup)
        self.content.ids["cur_X"].text = str(self.TravelX)
        self.content.ids["cur_Y"].text = str(self.TravelY)
        self.content.ids["cur_Z"].text = str(self.TravelZ)
        self.content.ids["cur_panel"].text = str(self.cur_panel_num)

        if self.printer_connect() is False:
            return

        # set printer to home
        go_home(self.project_data)

        gcode = self.send_gcode_from_template(self.g_home)
        gcode1 = gcoder.LightGCode(gcode)
        self.print.startprint(gcode1)

        self._popup = Popup(title="Set reference point", content=self.content,
                            size_hint=(0.4, 0.4))
        self._popup.pos_hint={"center_x": .8, "center_y": .8}
        self._popup.open()
        self.project_data['CADMode']="None"

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
        self.project_data['CADMode']="None"

    def save_printer_port(self, txt_port):
        self.printer_post = txt_port
        self.dismiss_popup()

    def set_camera(self):
        # set camera device
        content = EditPopup(save=self.save_camera_port, cancel=self.dismiss_popup)
        content.ids["text_port"].text = self.cam_port
        self._popup = Popup(title="Select Camera port", content=content,
                            size_hint=(0.5, 0.4))
        self._popup.open()
        self.project_data['CADMode']="None"

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
        #TODO
        #self.printer_disconnect()
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


### Application
class MyApp(App):

    def check_resize(self, instance, x, y):
        # resize X
        if x > MAX_SIZE[0]:
            Window.size = (MAX_SIZE[0], Window.size[1])
        # resize Y
        if y > MAX_SIZE[1]:
            Window.size = (Window.size[0], MAX_SIZE[1])
    def mainscreen(self):
        screen["screen"] = "main"

    def build(self):
        self.title = 'THT Soldering Robot'
        Window.size = MAX_SIZE
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
