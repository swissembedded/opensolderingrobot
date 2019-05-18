
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

import gerber
from gerber.render.cairo_backend import GerberCairoContext
from gerber.excellon import DrillHit

MAX_SIZE = (1280, 768)
Config.set('graphics', 'width', MAX_SIZE[0])
Config.set('graphics', 'height', MAX_SIZE[1])
Config.set('graphics', 'resizable', False)

#############################

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

class ScreenManagement(ScreenManager):
    pass


class ListScreen(Screen):
    def __init__(self, **kwargs):
        super(ListScreen, self).__init__(**kwargs)
        
        #Clock.schedule_interval(self.load_list, 0.2)
        #Clock.schedule_interval(self.show_status, 0.8)
    def import_nc(self):
        
        # Read gerber and Excellon files
        #top_copper = gerber.read('EnergyMeter_Panel2x3.DRR')
        nc_drill = gerber.read('EnergyMeter_Panel2x3.txt')
        print(nc_drill)
        hit_counts = nc_drill.hit_count()
        print(hit_counts)    
        """
        # Rendering context
        ctx = GerberCairoContext()
        # Create SVG image
        #top_copper.render(ctx)
        nc_drill.render(ctx, 'composite.svg')
        #"""
    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load(self):
        content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def show_save(self):
        content = SaveDialog(save=self.save, cancel=self.dismiss_popup)
        self._popup = Popup(title="Save file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def load(self, path, filename):
        with open(os.path.join(path, filename[0])) as stream:
            pass
            #self.text_input.text = stream.read()

        self.dismiss_popup()

    def save(self, path, filename):
        with open(os.path.join(path, filename), 'w') as stream:
            pass
            #stream.write(self.text_input.text)

        self.dismiss_popup()

    def load_list(self, dt):
        pass
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
    