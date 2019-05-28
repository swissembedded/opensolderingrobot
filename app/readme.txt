- ubuntu 18.04 64bit
	. install opensolderingrobot
		git clone https://github.com/swissembedded/opensolderingrobot.git
	. install anaconda
		(https://www.ceos3c.com/open-source/install-anaconda-ubuntu-18-04/)
		1. In your browser, download the Anaconda installer for Linux.
		2. Enter the following to install Anaconda for Python3.7:
			bash ~/Downloads/Anaconda3-2019.03-Linux-x86_64.sh
	. install kivy
		(https://anaconda.org/conda-forge/kivy)
		conda install -c conda-forge kivy
	. install pcb-tools
		
		pip install pcb-tools
		
		if not installed cario, should install cario
		
		sudo apt-get install libcairo2-dev
		#conda install -c conda-forge cairocffi 
		pip install cairocffi==0.6
	. install tsp-solver
		pip install tsp_solver
	. intall opencv
		pip install opencv-contrib-python
	. install printrun
		- install dependencies
			sudo apt install python3-serial python3-numpy cython3 python3-libxml2 python3-gi 
			python3-dbus python3-psutil python3-cairosvg libpython3-dev python3-appdirs python3-wxgtk4.0
			
			pip install pyserial 
			git clone git clone https://github.com/kliment/Printrun.git
			copy the printrun subfolder inside the printrun repository to the app folder of opensolderingrobot
	. install xclip xsel
		- sudo apt-get install xclip xsel
		