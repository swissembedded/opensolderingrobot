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
print("created data", prjdata)
# save it
data.write_project_data("temp/test", prjdata)
# load it again
prjdataload=data.read_project_data("temp/test")
print("loaded data",prjdataload)
if prjdata!=prjdataload:
	print("created and loaded data are different!")
else:
	print("created and loaded data are identical!")

# MENU PROGRAM
# import excellon file
ncdata=excellon.load_nc_drill("../testdata/Project Outputs for PCB_Project/testprint.TXT")
# convert to dialog tools
tools=excellon.convert_to_tools(ncdata)
print("tools", tools)
# convert it to json
soldertoolpath=excellon.convert_to_json(ncdata)
print("soldertoolpath",soldertoolpath)
prjdata['SolderToolpath']=soldertoolpath
# select by diameter
soldertoolpathtool=excellon.select_by_tool(soldertoolpath, 1, 0)
print("soldertoolpath tool selected",soldertoolpathtool)

# select by coordinate
soldertoolpathpos=excellon.select_by_position(soldertoolpath, 80.238, 53.086,0)
print("soldertoolpath position selected",soldertoolpathpos)
# deselect drill hole by coordinate
soldertoolpathpos=excellon.deselect_by_position(soldertoolpath, 80.238, 53.086)
print("soldertoolpath position deselected",soldertoolpathpos)

# select reference points
soldertoolpathref1=excellon.set_reference_1(soldertoolpath, 80.238, 53.086)
ref1index=excellon.get_reference_1(soldertoolpathref1)
print("ref1",ref1index)

soldertoolpathref2=excellon.set_reference_2(soldertoolpath, 54.991, 64.897)
ref2index=excellon.get_reference_2(soldertoolpathref2)
print("ref2",ref2index)
if ref1index==0 and ref2index==19:
	print("ref ok")
else:
	print("ref not ok")
# transform coordinate from click event
# create g-code for soldering
# create g-code for home
# create g-code for go xyz
# convert g-code to array
