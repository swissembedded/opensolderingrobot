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
# create a new project
prjdata=data.init_project_data()
print("created data", prjdata)
# save it
data.write_project_data("temp/test", prjdata)
prjdataload=data.read_project_data("temp/test")
print("loaded data",prjdataload)
if prjdata!=prjdataload:
	print("created and loaded data are different!")
else:
	print("created and loaded data are identical!")
# load it

# import excellon file
# convert it to json
# select diameter
# select drill hole by coordinate
# deselect drill hole by coordinate
# transform coordinate from click event

# create g-code for soldering
# create g-code for home
# create g-code for go xyz
# convert g-code to array
