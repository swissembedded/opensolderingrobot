# Test libraries
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

import data
import excellon
import robotcontrol

# using folder tmp

# MENU PROJECT
# create a new project
prjdata=data.init_project_data()
# save it
data.write_project_data("temp/test", prjdata)
# load it again
prjdataload=data.read_project_data("temp/test")
if prjdata!=prjdataload:
	print("nok created and loaded data are different!")
	print("created data", prjdata)
	print("loaded data",prjdataload)
else:
	print("ok created and loaded data are identical!")

# MENU PROGRAM
# import excellon file
ncdata=excellon.load_nc_drill("../testdata/Project Outputs for PCB_Project/testprint.TXT")
# convert to dialog tools
tools=excellon.convert_to_tools(ncdata)
num=len(tools)
if num==1:
	print("ok tools")
else:
	print("nok tools", num, tools)
# convert it to json
soldertoolpath=excellon.convert_to_json(ncdata)
num=len(soldertoolpath)
if num==40:
	print("ok soldertoolpath json")
else:
	print("nok soldertoolpath",num, soldertoolpath)

# select by coordinate
excellon.select_by_position(soldertoolpath, 80.238, 53.086,0)
num=excellon.get_number_selected_solderpoints(soldertoolpath)
if num==1:
	print("ok soldertoolpath pos selected")
else:
	print("nok soldertoolpath pos selected", num, soldertoolpath)

# deselect drill hole by coordinate
excellon.deselect_by_position(soldertoolpath, 80.238, 53.086)
num=excellon.get_number_selected_solderpoints(soldertoolpath)
if num==0:
	print("ok soldertoolpath pos deselected")
else:
	print("nok soldertoolpath pos deselected", num, soldertoolpath)

# select by diameter
excellon.select_by_tool(soldertoolpath, 1, 0)
num=excellon.get_number_selected_solderpoints(soldertoolpath)
if num==40:
	print("ok soldertoolpath tool selected")
else:
	print("nok soldertoolpath tool selected",num, soldertoolpath)

# select reference points
ref1x=97.738
ref1y=53.086
excellon.set_reference_1(soldertoolpath, ref1x, ref1y)
ref1index=excellon.get_reference_1(soldertoolpath)

ref2x=54.991
ref2y=67.437
excellon.set_reference_2(soldertoolpath, ref2x, ref2y)
ref2index=excellon.get_reference_2(soldertoolpath)
if ref1index==5 and ref2index==20:
	print("ok ref")
else:
	print("nok ref", refindex1,refindex2)

# optimize the ToolPathSorting
excellon.optimize_soldertoolpath(soldertoolpath)
num=excellon.get_number_solderpoints(soldertoolpath)
if num==40:
	print("ok optimize")
else:
	print("nok optimize", num)
# get first soldering point (per definition it is the first reference point)
num=excellon.get_solderpoint(soldertoolpath,0)
if num==ref1index:
	print("ok first soldering point")
else:
	print("nok first soldering point")

# get tool area
xmin, xmax, ymin, ymax=excellon.get_nc_tool_area(soldertoolpath)
if xmin==54.441 and xmax==98.288 and ymin==52.536 and  ymax==67.987:
	print("ok nc tool area")
else:
	print("nok nc tool area",xmin,xmax, ymin, ymax)
# get nc drill position from pixel position
# just assume pixel have scale of 100
xt, yt=excellon.get_nc_tool_position(soldertoolpath,0,0,(xmax-xmin)*100.0,(ymax-ymin)*100.0)
if xt==xmin and yt==ymin:
	print("ok nc tool position min")
else:
	print("nok nc tool position min", xt, yt)

xt, yt=excellon.get_nc_tool_position(soldertoolpath,(xmax-xmin)*100.0,(ymax-ymin)*100.0,(xmax-xmin)*100.0,(ymax-ymin)*100.0)
if xt==xmax and yt==ymax:
	print("ok nc tool position max")
else:
	print("nok nc tool position max", xt, yt)

# get pixel position from nc drill position
xt, yt=excellon.get_pixel_position(soldertoolpath,xmin,ymin,(xmax-xmin)*100.0,(ymax-ymin)*100.0)
if xt==0 and yt==0:
	print("ok pixel position min")
else:
	print("nok pixel position min", xt, yt)
xt, yt=excellon.get_pixel_position(soldertoolpath,xmax,ymax,(xmax-xmin)*100.0,(ymax-ymin)*100.0)
if xt==(xmax-xmin)*100.0 and yt==(ymax-ymin)*100.0:
	print("ok pixel position max")
else:
	print("nok pixel position max", xt, yt)
panel=[]
excellon.set_num_panel(panel, 5)
num=excellon.get_num_panel(panel)
if num==5:
	print("ok num panel")
else:
	print("nok num panel",num)

excellon.set_panel_reference_1(panel,0,ref1x+10,ref1y+10,10)
x1,y1,z1 = excellon.get_panel_reference_1(panel,0)
if x1 == ref1x+10 and y1 == ref1y+10 or z1 == 10:
	print("ok panel ref 1")
else:
	print("nok panel ref 1", x1, y1, z1)

excellon.set_panel_reference_2(panel,0,ref2x+10,ref2y+10,10)
x2,y2,z2 = excellon.get_panel_reference_2(panel,0)
if x2 == 10+ref2x and y2 == 10+ref2y or z2 == 10:
	print("ok panel ref 2")
else:
	print("nok panel ref 2", x2, y2, z2)

# soldering profile list for gui selection
solderingprofile=prjdata['SolderingProfile']
list=excellon.get_list_soldering_profile(solderingprofile)
if len(list)==len(solderingprofile['SolderingProfile']):
	print("ok soldering profile list")
else:
	print("nok soldering profile list", len(list), len(solderingprofile), solderingprofile['SolderingProfile'])
# soldering profile first entry
firstprofile=excellon.get_soldering_profile(solderingprofile,0)
if firstprofile==solderingprofile['SolderingProfile'][0]:
	print("ok sodering profile")
else:
	print("nok soldering profile")

# make array out of gcode
garray=robotcontrol.make_array("1\n2\n3\n")
if len(garray) == 3:
	print("ok gcode array")
else:
	print("nok gcode array")

# create g-code for home
#go_xyz(prjdata, x,y,z)
gcode=robotcontrol.go_xyz(prjdata, 1,2,3)
if "G1 X1 Y2 Z3" in gcode:
	print("ok go xyz")
else:
	print("nok goxyz", gcode)

#go_home(prjdata)
gcode=robotcontrol.go_home(prjdata)
if "G28" in gcode and "G90" in gcode:
	print("ok home")
else:
	print("nok home", gcode)

gcode=robotcontrol.strip_comment("G28; this is a comment")
if gcode=="G28":
	print("ok strip")
else:
	print("nok strip",gcode)
	
# create g-code for soldering
prjdata['Panel']=panel
prjdata['SolderToolpath']=soldertoolpath
gcode=robotcontrol.panel_soldering(prjdata, [0], False)
print("soldering", gcode)
