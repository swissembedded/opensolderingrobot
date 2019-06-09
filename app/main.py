# Main routine
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
        ### make project data available in class
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
            touchxp=widthp-(touchxp-posxp)
            touchyp=touchyp-posyp

        xnc, ync = excellon.get_nc_tool_position(soldertoolpath,touchxp,touchyp,width*scale,height*scale)
        # out of image
        print("pos:", touch.pos, self.pos, self.size, posxp, posyp, "xnc ", xnc, "ync ", ync, xmin, xmax, ymin, ymax)

        if xnc < xmin or xnc > xmax or ync < ymin or ync > ymax:
            return
        # perform action on mode
        if mode=="Select":
            excellon.select_by_position(soldertoolpath, xnc, ync, selectedsolderingprofile)
        elif mode=="Deselect":
            excellon.deselect_by_position(soldertoolpath, xnc, ync)
        elif mode=="Ref1":
            excellon.set_reference_1(soldertoolpath, xnc, ync)
        elif mode=="Ref2":
            excellon.set_reference_2(soldertoolpath, xnc, ync)
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
    get_panel_ref1 = ObjectProperty(None)
    set_panel_ref1 = ObjectProperty(None)
    get_panel_ref2 = ObjectProperty(None)
    set_panel_ref2 = ObjectProperty(None)
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

    def init_project(self):
        # init data
        self.project_file_path = ""
        self.project_data=data.init_project_data()
        self.project_data['CADMode']="None"
        self.ids["img_cad_origin"].set_cad_view(self.project_data)
        self.ids["img_cad_origin"].redraw_cad_view()
        self.capture = None
        self.print = None
        self.paneldisselection=[]
        try:
            self.camera_disconnect()
            self.camera_connect()
            self.printer_disconnect()
            self.printer_connect()
        except Exception as e:
            print(e, "cam or printer start problem")
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
            self.project_file_path =  os.path.expanduser(filename[0])
            self.project_data=data.read_project_data(self.project_file_path)
            self.paneldisselection=[]
            try:
                self.camera_disconnect()
                self.camera_connect()
                self.printer_disconnect()
                self.printer_connect()
            except Exception as e:
                print(e, "cam or printer start problem")
                pass

            self.ids["img_cad_origin"].set_cad_view(self.project_data)
            self.ids["img_cad_origin"].redraw_cad_view()
        except:
            ### if not proper project file
            print("Problem loading file")
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
        self.project_file_path = os.path.expanduser(os.path.join(path, filename))
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
            nc_file_path  = os.path.expanduser(filename[0])
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
        self.project_data['CADMode']="Select"

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
        num = max(1, num)
        num = min(self.project_data['Setup']['MaxPanel'], num)
        excellon.set_num_panel(self.project_data['Panel'], num)
        self.dismiss_popup()

    def set_reference_panel(self):
        #  show dialpad
        print("ref")
        self.ids["tab_panel"].switch_to(self.ids["tab_panel"].tab_list[0])
        self.content = ControlPopup(controlXYZ=self.control_XYZ, set_panel_ref1=self.set_panel_ref1, set_panel_ref2=self.set_panel_ref2, get_panel_ref1=self.get_panel_ref1, get_panel_ref2=self.get_panel_ref2, cancel=self.dismiss_popup)
        self.content.ids["cur_X"].text = format(self.project_data['Setup']['TravelX'],".2f")
        self.content.ids["cur_Y"].text = format(self.project_data['Setup']['TravelY'],".2f")
        self.content.ids["cur_Z"].text = format(self.project_data['Setup']['TravelZ'],".2f")
        self.content.ids["cur_panel"].text = "1"
        self._popup = Popup(title="Set reference point", content=self.content,
                            size_hint=(0.4, 0.4))
        self._popup.pos_hint={"center_x": .8, "center_y": .8}
        self._popup.open()
        self.project_data['CADMode']="None"

        # home printer
        gcode=robotcontrol.go_home(self.project_data)
        self.queue_printer_command(gcode)

    def control_XYZ(self, axis, value):
        ### click any button on dialpad, calculate new position
        index=int(self.content.ids["cur_panel"].text)
        x=float(self.content.ids["cur_X"].text)
        y=float(self.content.ids["cur_Y"].text)
        z=float(self.content.ids["cur_Z"].text)

        if axis == "X":
            x += float(value)
        elif axis == "Y":
            y += float(value)
        elif axis == "Z":
            z += float(value)
        elif axis == "HomeXY":
            x=self.project_data['Setup']['TravelX']
            y=self.project_data['Setup']['TravelY']
        elif axis == "HomeZ":
            z=self.project_data['Setup']['TravelZ']

        index = max(1, index)
        index = min(self.project_data['Setup']['MaxPanel'], index)
        x=max(self.project_data['Setup']['MinX'],x)
        x=min(self.project_data['Setup']['MaxX'],x)
        y=max(self.project_data['Setup']['MinY'],y)
        y=min(self.project_data['Setup']['MaxY'],y)
        z=max(self.project_data['Setup']['MinZ'],z)
        z=min(self.project_data['Setup']['MaxZ'],z)

        self.content.ids["cur_panel"].text = str(index)
        self.content.ids["cur_X"].text = format(x,".2f")
        self.content.ids["cur_Y"].text = format(y,".2f")
        self.content.ids["cur_Z"].text = format(z,".2f")

        # go xyz printer
        gcode=robotcontrol.go_xyz(self.project_data,x,y,z)
        self.queue_printer_command(gcode)

    def set_panel_ref1(self):
        ### click set1 button on dialpad
        index=int(self.content.ids["cur_panel"].text)
        index=min(index,excellon.get_num_panel(self.project_data['Panel']))
        index=max(index,1)

        x=float(self.content.ids["cur_X"].text)
        y=float(self.content.ids["cur_Y"].text)
        z=float(self.content.ids["cur_Z"].text)
        excellon.set_panel_reference_1(self.project_data['Panel'], index-1, x, y, z)

    def set_panel_ref2(self):
        ### click set2 button on dialpad
        index=int(self.content.ids["cur_panel"].text)
        x=float(self.content.ids["cur_X"].text)
        y=float(self.content.ids["cur_Y"].text)
        z=float(self.content.ids["cur_Z"].text)
        excellon.set_panel_reference_2(self.project_data['Panel'], index-1, x, y, z)

    def get_panel_ref1(self):
        ### click on get1 button on dialpad
        index=int(self.content.ids["cur_panel"].text)
        x,y,z = excellon.get_panel_reference_1(self.project_data['Panel'], index-1)
        if x==-1 and y==-1 and z==-1:
            x=self.project_data['Setup']['TravelX']
            y=self.project_data['Setup']['TravelY']
            z=self.project_data['Setup']['TravelZ']
        self.content.ids["cur_X"].text = format(x,".2f")
        self.content.ids["cur_Y"].text = format(y,".2f")
        self.content.ids["cur_Z"].text = format(z,".2f")
        # go xyz printer
        gcode=robotcontrol.go_xyz(self.project_data,x,y,z)
        self.queue_printer_command(gcode)

    def get_panel_ref2(self):
        ### click on get2 button on dialpad
        index=int(self.content.ids["cur_panel"].text)
        x,y,z = excellon.get_panel_reference_2(self.project_data['Panel'], index-1)
        if x==-1 and y==-1 and z==-1:
            x=self.project_data['Setup']['TravelX']
            y=self.project_data['Setup']['TravelY']
            z=self.project_data['Setup']['TravelZ']
        self.content.ids["cur_X"].text = format(x,".2f")
        self.content.ids["cur_Y"].text = format(y,".2f")
        self.content.ids["cur_Z"].text = format(z,".2f")
        # go xyz printer
        gcode=robotcontrol.go_xyz(self.project_data,x,y,z)
        self.queue_printer_command(gcode)

    def select_pcb_in_panel(self):
        num=excellon.get_num_panel(self.project_data['Panel'])
        content = EditPopup(save=self.save_pcb_in_panel, cancel=self.dismiss_popup)
        content.ids["btn_connect"].text = "Save"
        content.ids["text_port"].text = ""
        self._popup = Popup(title="Select Panels to exclude from Soldering example \"1,2\"", content=content,
                            size_hint=(0.5, 0.4))
        self._popup.open()
        self.project_data['CADMode']="None"

    def save_pcb_in_panel(self, txt_port):
        # set array of panels
        excludepanels=txt_port.split(",")
        panel=[]
        for p in range(excellon.get_num_panel(self.project_data['Panel'])):
            if str(p+1) in excludepanels:
                panel.append(p)
        self.paneldisselection=panel
        self.dismiss_popup()

    def start_soldering(self):
        ### toolbar start soldering button
        # prepare panel
        panel=[]
        for p in range(excellon.get_num_panel(self.project_data['Panel'])):
            if p not in self.paneldisselection:
                panel.append(p)
        # print
        print("panel", panel)
        gcode=robotcontrol.panel_soldering(self.project_data, panel, False)
        self.queue_printer_command(gcode)

    def test_soldering(self):
        ### toolbar test soldering button
        # prepare panel
        panel=[]
        for p in range(excellon.get_num_panel(self.project_data['Panel'])):
            if p not in self.paneldisselection:
                panel.append(p)
        # print
        gcode=robotcontrol.panel_soldering(self.project_data, panel, True)
        self.queue_printer_command(gcode)

    def pause_soldering(self):
        ### toolbar pause soldering button
        if self.print.printing:
            self.print.pause()

    def resume_soldering(self):
        ### toolbar resume soldering button
        if self.print.printing:
            self.print.resume()

    def stop_soldering(self):
        ### toolbar stop soldering button
        if self.print.printing:
            self.print.cancelprint()

    def queue_printer_command(self, gcode):
        garray=robotcontrol.make_array(gcode)
        #print("gcode raw", gcode, garray)

        gcoded = gcoder.LightGCode(garray)
        #print("gcoded", gcoded)
        if hasattr(self,'print') and self.print is not None:
            if not self.print.online or not self.print.printer:
                print("Problem with printer", self.print.online, self.print.printer)
            if self.print.printing:
                self.print.send(gcoded)
            else:
                self.print.startprint(gcoded)
        else:
            print("Problem with printer interface")
    #### Connect menu
    def set_printer(self):
        ### Connect Menu /  Connect Printer
        content = EditPopup(save=self.save_printer_port, cancel=self.dismiss_popup)
        content.ids["text_port"].text = self.project_data['Setup']['RobotPort']
        self._popup = Popup(title="Select Printer port", content=content,
                            size_hint=(0.5, 0.4))
        self._popup.open()
        self.project_data['CADMode']="None"

    def save_printer_port(self, txt_port):
        self.project_data['Setup']['RobotPort'] = txt_port
        try:
            self.printer_disconnect()
            self.printer_connect()
        except  Exception as e:
            print(e,"exception save robot port")
            pass
        self.dismiss_popup()

    def set_camera(self):
        # set camera device
        content = EditPopup(save=self.save_camera_port, cancel=self.dismiss_popup)
        content.ids["text_port"].text = self.project_data['Setup']['CameraPort']
        self._popup = Popup(title="Select Camera port", content=content,
                            size_hint=(0.5, 0.4))
        self._popup.open()
        self.project_data['CADMode']="None"

    def save_camera_port(self, txt_port):
        self.project_data['Setup']['CameraPort'] = txt_port
        try:
            self.camera_disconnect()
            self.camera_connect()
        except  Exception as e:
            print(e,"exception save cam port")
            pass
        self.dismiss_popup()

    def dismiss_popup(self):
        self._popup.dismiss()

    def camera_connect(self):
        ### connect camera
        self.capture = VideoCaptureAsync(self.project_data['Setup']['CameraPort'])
        self.capture.start()

    def camera_disconnect(self):
        if self.capture is not None:
            self.capture.stop()
            self.capture = None

    def printer_connect(self):
        if self.print is None:
            self.print = printcore(self.project_data['Setup']['RobotPort'], 115200)

    def printer_disconnect(self):
        if self.print is not None:
            self.print.disconnect()
            self.print = None

    def show_status(self, dt):
        self.ids["lbl_layer_status"].text="Layer: "+self.project_data['SolderSide']
        self.ids["lbl_cad_status"].text="CADMode: "+self.project_data['CADMode']

        profile=excellon.get_list_soldering_profile(self.project_data['SolderingProfile'])
        self.ids["lbl_profile_status"].text="Profile: "+profile[self.project_data['SelectedSolderingProfile']]
        if hasattr(self,'capture') and self.capture is not None:
            self.ids["lbl_cam_status"].text="Camera: Connected"
        else:
            self.ids["lbl_cam_status"].text="Camera: Not Found"
        #printer
        if hasattr(self,'print') and self.print is not None:
            if self.print.printer is None:
                self.ids["lbl_printer_status"].text="Robot: No 3d printer found"
            elif self.print.printing:
                if len(self.print.mainqueue)>0:
                    self.ids["lbl_printer_status"].text="Robot: Soldering "+ str(round(float(self.print.queueindex) / len(self.print.mainqueue)*100,2))+"%"
                else:
                    self.ids["lbl_printer_status"].text="Robot: Soldering"
            elif self.print.online:
                self.ids["lbl_printer_status"].text="Robot: Idle"
            else:
                self.ids["lbl_printer_status"].text="Robot: Connected"
        else:
            self.ids["lbl_printer_status"].text="Robot: Not Found"


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
