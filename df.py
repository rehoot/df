#!/opt/local/bin/python
# dfcurs06.py
#
# To Do:
# 1) error checking around Popen
# 2) adjust screen dimensions when user changes
#    screen size (need to access curses.getmaxyx())
# 3) genealize the main class to reuse it for
#    pop-ups that need scrolling and selection
# 4) generalize ShortcutWin to be a general popup
#    for static text, then transfer the shortcut
#    stuff to the new, scrolling popup.
# 5) create default config file if one is not found
#
# df.py version 0.03 for python 3+
##################################################################
# This file is df.py = "directory freedom (imitation)".
# df.py is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3
# of the License.
#
# df.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public
# License along with lgit. If not, see
# <http://www.gnu.org/licenses/>.
##################################################################


import sys, curses, os, subprocess, posix, getopt 
import configparser

# make the status line global so I can grab
# for my debug print routine
HEADER_LINES = 3
SPACE_BETWEEN_COLUMNS = 2
SHELL_OPTIONS ="-is" 
SHELL_PGM = "bash"
#
# Globals for read the config file:
# (note that the 'portlist' is a list object
# that will be assembled later using the 
# systems filename separator--an attemp
# at portability).
conf_file_portlist = ["~", ".dfconfig"]
g_selected_txt = ""
g_opts = {}
g_shortcuts = {}

def usage():
	print("usage:\ndf.py ")
	print("--help")
	print("-h")
	print("	this help message.")
	print("A future option might allow an override to the default config file.")
	# ADD INSTRUCTIONS HERE
	# ADD INSTRUCTIONS HERE
	# ADD INSTRUCTIONS HERE
	# ADD INSTRUCTIONS HERE
	# ADD INSTRUCTIONS HERE

class ShortcutWin():
	"""class ShortcutWin
	This will display a window that contains a list of 
	shortcuts that are coded in the ~/.dfconfigfile.
	This will return the key for the shortcut (usually
	a one- or two-letter code).

	Pass the parent window handle and a dictionary object
	that contains the shortcuts.

	###call redrawwin() from the parent window after this closes
	"""
	def __init__(self, window, scut_dict):
		global g_shortcuts

		(max_y, max_x) = window.getmaxyx()
		self.left = 4
		self.right = max_x - 4
		self.top = 4
		self.bot = max_y - 4
		self.width = self.right - self.left
		self.height = self.bot - self.top

		self.window = window.derwin(self.height, self.width, 4, 4)
		self.window.erase()
		self.window.box()
	
		j = 0
		for mykey in g_shortcuts.keys():
			if j < (self.height - 1):
				self.window.addstr(j + 1, 1, mykey + "  " + g_shortcuts[mykey])
			j += 1

	def attrset(self, attr):
		"""ShortcutWin.attrset()
		This will set the curses display attributes.
		First define a color pair, then call something
		like this:
		myshortcutwin.attrset(curses.color_pair(3))
		"""
		self.window.attrset(attr)
		return(0)

	def select_opt(self):
		c = self.window.getch()
		return(c)
	
	def erase(self):
		self.window.erase()
		return(0)

class WinFrame():
	"""Class WinFrame.
	This is a simple window frame that includes a few functions
	for keeping track of the cursor location and frame 
	dimensions so that the calling routine can display
	information on the screen.  The calling routine will
	contain all the logic for handling input.

	Parms:
	top, left, bot, right are zero-based offsets relative
	to the parent window extents.
	"""
	def __init__(self, parent_window, top, left, bot, right, \
	report_cols=1, border=0):
		self.left = left + border
		self.right = right - border
		self.top = top + border
		self.bot= bot - border
		self.border = border #inter = 1
		# CHECK THESE. I HAD A PROBLEM WITH ADDSTR WHEN THE
		# "+1" WAS ADDED BELOW.
		self.height = self.bot - self.top - 2*border ##+ 1
		self.width = self.right - self.left - 2*border ###+ 1
		self.scrn = parent_window.derwin(self.height, self.width, \
			self.top, self.left)
		self.row = 0 # main row pointer
		self.col = 0 # main col pointer
		# rpt_cos is the number of "newpaper columns," usually 1-3
		self.report_cols = report_cols
	
	def addstr(self, row, col, txt, format=curses.A_NORMAL):
		self.scrn.addstr(self.border + row, self.border + col, txt, format)

	def clear(self):
		"""This should probably print blanks to the full display area.
		"""
		self.scrn.clear()
		return(0)

#
	def get_height(self):
		return(self.height)

	def get_max_yx(self):
		"""WinFrame.get_max_yx()
		Return the maximum row and column index
		(zero-based offsets)
		
		The name was derived from the getmaxyx() function
		in the curses package.
		"""
		(max_y, max_x) = self.scrn.getmaxyx()
		return([max_y, max_x])

	def get_col(self):
		"""WinFrame.get_col()
		Returns a zero-based col index into the 
		selected window frame.
		"""
		return(self.col)

	def get_row(self):
		"""WinFrame.get_row()
		Returns a zero-based row index into the 
		selected window frame.
		"""
		return(self.row)
		
	def get_frame_width(self):
		"""WinFrame.get_frame_width
		return width of the frame in characters
		"""
		return(self.width)

	def incr_col(self, incr):
		"""winframe.incr_col()
		set the current col index (zero-based)
		if it is within the legal range.  return the
		resulting col value.
		"""
		tmp_col = self.col + incr
		if tmp_col >=0 and tmp_col <= self.right:
			self.col = tmp_col
		return(self.col)

	def incr_row(self, incr):
		"""winframe.incr_row()
		set the current row index (zero-based)
		if it is within the legal range.  return the
		resulting row value.
		"""
		tmp_row = self.row + incr
		if tmp_row >=0 and tmp_row <= self.bot:
			self.row = tmp_row
		return(self.row)
	
	def restore_cursor(self):
		"""WinFrame.move()
		This will restore the cursor to the currently registered
		window row and column.
	
		Use this only after display text to the non-text area
		(such as the status bar).
		"""
		self.scrn.move(self.row + self.border, \
			self.col + self.border)
		return(0)

	def refresh(self):
		"""WinFrame.refresh()
		I'm not sure when this is needed.
		"""
		self.scrn.refresh()
		return(0)

	def set_col(self, new_col):
		"""WinFrame.set_col()
		Set the current window col if it is legal,
		and return the final value of col.
		"""
		if new_col >= 0 and new_col <= self.right:
			self.col = new_col
		return(self.col)

	def set_row(self, new_row):
		"""WinFrame.set_row()
		Set the current window row if it is legal,
		and return the final value of row.
		"""
		if new_row >= 0 and new_row <= self.bot:
			self.row = new_row
		return(self.row)

#
#
class WinHeader(WinFrame):
	"""class WinHeader(WinFrame)
	This will modify the WinFrame class to 
	describe a small, display-only window that will be used
	to post some status info at the top of 
	a logical window (i.e., allow for a menue line,
	and lines that display the current path and currently-
	selected item.

	This window does not track cursor location and should
	not be used for user input.
	"""
	key_def_row = 0
	path_row = 1
	selected_txt_row = 2
	#
	def __init__(self, parent_window, top, left, bot, right, border=0):
		WinFrame.__init__(self, parent_window, top, left, bot, right, \
			border=border)
		self.header_txt = []
		self.header_prefix_txt = []
		if (bot - top) < 2:
			# The specified dimensions are not tall enough
			raise Exception("Status Bar Not Tall Enough")
		self.header_txt.append( "S=open shell; O=open file; " \
			+ "##<ENTER> goto #; h=left; l=right; j=down; k=up")
		self.header_txt.append("")
		self.header_txt.append("")
		self.header_prefix_txt = ["", "Path: ", "Selected Item: "]
		self.scrn = parent_window.derwin(self.height, self.width, \
			self.top, self.left)
		self.display_all()

	def clear(self):
		"""WinHeader.clear()
		Clear only the header window.
		"""
		#width = self.right - self.left + 1
		#for j in range(self.top, self.bot + 1):
		#	self.addstr(j,0, " " * width)
		self.scrn.clear()
		return(0)

	def display_all(self):
		"""WinHeader.display_all()
		Display all the header_txt and prefix values
		"""
		for j in range(len(self.header_txt)):
			if j >= self.height:
				raise Exception("There are more lines of header text than header lines")
			self.scrn.addstr(j,0, (self.header_prefix_txt[j] \
				+ self.header_txt[j] )[0:self.width])
		return(0)

	def display_header(self, header_idx):
		"""WinHeader.display_header()
		This will display the header associated with the
		given index (zero-based). 
		"""
		# header 1 is the menu line in df.py
		if header_idx > self.height:
			raise Exception("header_idx is greater than header height")
		new_txt = self.header_prefix_txt[header_idx] + \
			self.header_txt[header_idx] \
			 + " "*self.width
		self.scrn.addstr(header_idx, 0, new_txt[0:self.width-1])
		return(0)

	def get_header_txt(self, header_idx, format_code=0):
		"""WinHeader.get_header_txt()
		This will return the main value used on the header 
		line at the specified index (zero-based row index).
		
		This is a generic routine and does not perform any
		data cleansing--maybe in the future I will add some
		codes to perform things like standardizing path names
	
		format_code is not used.
		"""
		return(self.header_txt[header_idx])

	def set_header_txt(self, header_idx, txt):
		"""WinHeader.setselectedtxt()
		set the main value of the give header line (zero-based
		row index) and update the display.

		you can choose to put a header prefix
		into a separate field using set_header_prefix_txt().
		"""
		while len(self.header_txt) <= header_idx:
			self.header_txt.append("") 
		while len(self.header_prefix_txt) <= header_idx:
			self.header_prefix_txt.append("") 
		self.header_txt[header_idx] = txt
		self.display_header(header_idx)
		return(0)

	def set_header_prefix_txt(self, txt, header_idx):
		"""WinHeader.setselectedtxt()
		Set the prefix text for the given header row (zero-based
		row index) and update the display.

		Every header_txt value must have a string value for
		the header_prefix_txt ("" is OK).

		The prefix is useful if you want to keep the dynamic
		part of the header clean so you can update it 
		without having to chage the prefix text.
		"""
		while len(self.header_prefix_txt) <= header_idx:
			self.header_prefix_txt.append("") 
		self.header_prefix_txt[header_idx] = txt
		self.display_header(header_idx)
		return(0)
#
#
#
class SelectionWindow():
	"""class SelectionWindow
	This is the main class in this program.  Right now it is 
	essentiall a File/Open dialog box.

	This class will define two
	"frames:" a header frame for a menu and a scrolling text
	display that will list items and allow the user to select one.

	This class will be generalized in the future, but for now the
	main() function will pass a list of file names to this and 
	set the format code to 0 for regular files and 1 for directories.
	The SelectionWindow.key_loop() function will get input from the user
	and issue a return code [1, directory_name] if the user selected
	a directory (then the main() function will create a new list of 
	files from that directory.  When the user hits ENTER on a regular
	file, the key_loop() function will return [0, file_name] and 
	the program will end.

	The return of the selected file name can be used from a main program
	that needed to provide user input to select a file name.

	While browsing the file tree, the user can press 'F' to show a list
	of 'favorites,' which allow the user to go to a favoriate directory.
	The user can press 'S' to open a shell in the current directory or
	press 'O' to issue the 'open' command that should open the appriopriate
	program and open the file.
	"""
	def __init__(self, window, report_cols, col_minmax, buff, formats, the_path):
		# parms:
		# window = a curses screen object--usually a full screen or nearly full.
		# report_cols = number of report columns to display (same
		#        idea as newspaper columns). Zero means automatic.
		# col_minmax = a list that contains a min/max list 
		#   for each colum (min/max charcter_col width; NOT USED YET)
		# buff = a list of strings to display
		# formats = a list of 0 for regular files or 1 for directories.
		# the_path = a path that is the starting basis for the file list.
		#
		global	 HEADER_LINES, SPACE_BETWEEN_COLUMNS
		self.window = window
		self.ibuff = buff
		self.ibuff_idx = 0
		# Check the maximum width of the input buffer
		self.max_txt_width = 0
		for j in range(len(self.ibuff)):
			if len(buff[j]) > self.max_txt_width:
				self.max_txt_width = len(buff[j])
		if report_cols == 0:
			# zero means auto-detect the number of report
			# columns.
			(max_y, max_x) = self.window.getmaxyx()
			tmp = int(self.max_txt_width + 5 + \
				SPACE_BETWEEN_COLUMNS) / max_x
			if tmp < 1:
				self.report_cols = 1
			else:
				self.report_cols = tmp
			
		# top_ibuff_idx is the ibuff_idx of the
		# first line displayed on the screen (used
		# to manage scrolling of the text)
		self.top_ibuff_idx = 0
		self.formats = formats
		self.frames = []
		# 
		# Window setup
		# disable the normal echo of characters to the screen
		curses.noecho()
		# the cbreak command helps to process key strokes instantly
		curses.cbreak()
		# attemp to allow arrow keys (didn't work):
		curses.meta(1)
		# activate the mouse (X-Term) and listen
		# for mouse click only:
		oldmouse=curses.mousemask(curses.BUTTON1_CLICKED)
		#self.displayscreen(self.startbuffrow_idx)
		if curses.has_colors():
			curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_YELLOW)
			curses.init_pair(2, curses.COLOR_CYAN, 0)
			curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_MAGENTA)
			curses.init_pair(4, curses.COLOR_MAGENTA, 0)
			curses.init_pair(5, curses.COLOR_RED, 0)
			curses.init_pair(6, curses.COLOR_YELLOW, 0)
			curses.init_pair(7, curses.COLOR_WHITE, 0)

		self.window.clear()
		self.window.refresh()
		# header/status bar frame:
		self.frames.append(WinHeader(self.window, 0, 0, HEADER_LINES, \
			self.window.getmaxyx()[1] - 1))
		self.frames[0].set_header_txt(1, the_path)
		#self.frames[0].refresh()
		#	
		# frame 1 will be the main display area. Others might
		# be used for menus, status line, debug info, etc
		(max_y, max_x) = self.window.getmaxyx()
		if report_cols == 0:
			# Calculate the number of 'newspaper columns' allowing for
			# some space between columns
			self.report_cols = int(max_x / (self.max_txt_width \
				+ 5 + SPACE_BETWEEN_COLUMNS))
			if self.report_cols < 1:
				self.report_cols = 1
		self.frames.append(WinFrame(self.window,HEADER_LINES, 0, \
			max_y, max_x, report_cols=self.report_cols ))
		#
		#
		self.display_buff()
		#self.frames[1].move(0,0)
		self.goto_buff_idx(0)

	def key_loop(self):
		"""SelectionWindow.key_loop()
		This is the main loop that captures key strokes and
		processes them.  I wanted to return a value so that 
		the program could return the value of selected text,
		so that means this cannot run from within __init__
		(because __init__ can't return a value)
		"""
		global SHELL_OPTIONS, SHEL_PGM, g_shortcuts
	
		while True:
			c = self.window.getch()# get an input char, then quit
			if 0<c<256:
				c = chr(c)
				if c.upper() == 'Q':
					break
				elif c.upper() == 'O':
					# open the file using the 'open' shell comand,
					# which can open GUI programs that are associated
					# with the file extension of the selected file.
					fpath = self.frames[0].get_header_txt(1) + os.sep + \
						self.ibuff[self.ibuff_idx]
					p1 = subprocess.Popen(["open", fpath])
					# this should be an asynchronous open
				elif c.upper() == 'F':
					# Favorites
					# show a pop-up menu with a list of favorites
					# capture input
					# set the path to the selected value
					subwin = ShortcutWin(self.window, g_shortcuts)
					# ATTRSET DOESNT WORK
					subwin.attrset(curses.color_pair(3))
					scut = chr(subwin.select_opt())
					subwin.erase()
					subwin = None
					# Get the new path:
					try:
						new_dir = os.path.normpath(os.path.expanduser( \
							g_shortcuts[scut]))
						self.frames[0].set_header_txt(1, new_dir)
						# return and let the oute loop rebuild the list
						return([1, new_dir ])
					except KeyError:
						# The entered value is not in the shortcust
						# list, so restore the old window
						self.window.clear()
						self.frames[0].display_all()
						self.frames[1].clear()
						self.display_buff()
						##self.window.redrawwin()
				elif c.upper() == 'S':
					# Open a shell in the current directory
					# by returning code 2 and the path
					#myenv={"HOME": savedir}
					#os.putenv("HOME", savedir)
					self.window.keypad(0)
					curses.nocbreak()
					curses.echo()
					# I thought that the endwin() function would
					# ruin my curses session, but it didn't
					#?????????????????????????????????????????????????????????????????
					curses.endwin()
					p1 = subprocess.Popen([SHELL_PGM, SHELL_OPTIONS], 
						stdin=sys.stdin, stdout=sys.stdout)
					p1.communicate("cd " + self.frames[0].get_header_txt(1))
					# Attempt to restore my window
					curses.nocbreak()
					self.window.keypad(1)
					curses.echo()
					self.window.clear()
					self.frames[0].display_all()
					self.frames[1].clear()
					self.display_buff()

				elif c in ['l' '\t']:
					# move right
					self.goto_buff_idx(self.ibuff_idx + self.frames[1].get_height())
				elif c=='h':
					# move left
					self.goto_buff_idx(self.ibuff_idx - self.frames[1].get_height())
				elif c=='j':
					# move down
					self.goto_buff_idx(self.ibuff_idx + 1)
				elif c=='k':
					# move up
					self.goto_buff_idx(self.ibuff_idx - 1)
				elif c==os.linesep:
					# ENTER
					# If the current item is a directory (format code 1)
					# then append the current item to the current path
					# and submit it to reprocess the list.
					# The first zero is a code meaning 'get the listing of 
					# the new directory'
					next_dir = os.path.normpath(os.path.expanduser(\
					self.frames[0].get_header_txt(1) + os.sep \
						+ self.ibuff[self.ibuff_idx]))
					return([self.formats[self.ibuff_idx], next_dir ])

				elif c.isdigit():
					save = c
					while c not in ['\r', '\n'] and c.isnumeric():
						c = chr(self.window.getch())
						save += c
					# Use the number as a line number, convert it
					# to a buffer index and go to it.
					# Note that the minus sign is not captured
					# so entry of "-333" is captured as "333".
					self.goto_buff_idx(int(save) - 1)	
				else:
					#self.frames[0].set_header(1, "You pressed " + str(c) \
					#	+ ' ' + str(ord(c)))
					#self.window.refresh()
					pass
			else:
				# Not a regular character
				if c == curses.KEY_MOUSE:
					self.frames[1].refresh()	
					(mouse_id, mouse_x, mouse_y, mouse_z, button_state) = \
						curses.getmouse()
					if button_state == curses.BUTTON1_CLICKED:
						# the "-1" below is for the border -- i'll need abeter
						# way to do this.
						rcol = int(mouse_x / (self.max_txt_width + 5 + \
							SPACE_BETWEEN_COLUMNS))
						self.goto_buff_idx(mouse_y - HEADER_LINES - 2 + \
							self.top_ibuff_idx + rcol * self.frames[1].get_height())
						self.frames[1].refresh()#is this needed?
				elif c in [curses.KEY_UP]:
					# CHANGE THIS TO SET THE NEW POINTERS, THEN
					# RUN A SINGLE SCREEN UPDATE AT THE END?
					# OR MAYBE CALL A GENERIC FUNCTION TO PERFORM
					# THE SCREEN UPDATES
					if self.ibuff_idx > 0:
						self.goto_buff_idx(self.ibuff_idx - 1)
				elif c in [curses.KEY_DOWN]:
					# goto_buff will correct the move if needed
					self.goto_buff_idx(self.ibuff_idx + 1)
				elif c in [curses.KEY_NPAGE]:
					# page down/next page
					# Note: in Mac OS 10.6 on MacBook Pro, use SHIFT, 
					# Function, DOWN-ARROW,
					# but in Max with Xterm/X11, use Function DOWN-ARROW.
					# First go to the item on the current page that is two from 
					# the bottom, then go height*cols items down.
					self.goto_buff_idx(self.top_ibuff_idx + \
						self.frames[1].get_height() * self.report_cols - 3)
					self.goto_buff_idx(self.ibuff_idx + \
						self.frames[1].get_height() * self.report_cols)
				elif c in [curses.KEY_PPAGE]:
					# page up/previous page
					self.goto_buff_idx(self.top_ibuff_idx + 1 )
					self.goto_buff_idx(self.ibuff_idx - \
						self.frames[1].get_height() * self.report_cols)
				elif c == curses.KEY_RIGHT: #67
					self.goto_buff_idx(self.ibuff_idx + self.frames[1].get_height())
				elif c==curses.KEY_LEFT: #68
					self.goto_buff_idx(self.ibuff_idx - self.frames[1].get_height())
				elif c==curses.KEY_HOME:
					curses.beep()
					self.goto_buff_idx(0)
				elif c==curses.KEY_END:
					self.goto_buff_idx(len(self.ibuff)-1)
				else:
					#self.frames[0].set_header_txt(1, "you pressed " + \
					#	str(c) + ' ' + chr(c))
					#self.window.refresh()
					pass
	
	def display_buff(self):
		"""SelectionWindow.display_buff()
		Display the full input buffer.
		"""
		# ibuff_idx is used internally by frames[].addstr, so
		# set it properly before calling that function.
		#
		# Funtion:
		# 1) starting at the first ibuff_idx to display,
		# 2) display each line of ibuff as long is it can
		#    fit on the screen.
		save_idx = self.ibuff_idx
		len_ibuff = len(self.ibuff)
		self.frames[1].clear()
		# Given the first line of text that will be displayed,
		# how many lines of text will be displayed:
		remaining_lines = len_ibuff - self.top_ibuff_idx 
		if remaining_lines < (self.frames[1].get_height() * self.report_cols):
			# There are not enough remaining lines in the buffer
			# to fill the screen so adjust the ibuff index counter.
			# Note: The max range should be one higher than the max
			# value index into ibuff that I want to display, because
			# that is how the range() function works in python loops.
			max_range = self.top_ibuff_idx + remaining_lines 
		else:
			max_range = self.top_ibuff_idx + self.frames[1].get_height() \
				* self.report_cols
		wrow = 0
		wcol = 0
		junksave = max_range
		#
		for j in range(self.top_ibuff_idx, max_range):
			self.ibuff_idx = j
			# Display the line.
			self.frames[1].addstr(wrow , wcol , str(self.ibuff_idx + 1) + ") " \
				+ self.ibuff[j], curses.color_pair(self.formats[j]))
			wrow += 1
			if wrow >= self.frames[1].get_height():
				wrow = 0
				wcol += self.max_txt_width + 5 + SPACE_BETWEEN_COLUMNS
		self.frames[1].refresh()
		self.ibuff_idx = save_idx
		self.frames[1].restore_cursor()
		return(0)

	def goto_buff_idx(self, idx):
		"""SelectionWindow.goto_yx()
		Move the cursor the given buffer idx and highlight
		the display as needed.

		The paramaters passed to this function are always
		in terms of a buffer offset regardless of the number
		of display rows and columns.
		"""
		# Function:
		# 1) Unhighlight the current row
		# 2) Point to the new row and column
		# 3) Scroll if needed (under construction)
		# 4) Highlight the new row
		#
		#
		# CHANGES FOR NEWSPAPER COLUMNS:
		# a) Cacluation of bottom of screen needs to count
		#    the height as (hgt * cols) for the purposes
		#    of the buffer index
		# b) Use set_col whereever set_row is used
		#
		#
		# "wrow" means "window row" as opposed to "buffer row"
		if idx >= len(self.ibuff):
			idx = len(self.ibuff) - 1
		if idx < 0:
			idx = 0

		old_wrow = self.frames[1].get_row()
		old_wcol = self.frames[1].get_col()
		old_ibuff_idx = self.ibuff_idx
		#temp_wrow = old_wrow + idx - old_ibuff_idx
		#(w_height, w_width) = self.frames[1].get_max_yx()
		w_height = self.frames[1].get_height()
		w_width = self.frames[1].get_frame_width()
	
		end_idx = self.top_ibuff_idx + w_height * self.report_cols - 1
		if self.top_ibuff_idx	<= idx <= end_idx:
			# The new cursor location is on the current screen, 
			# and no scrolling is needed:
			# a) set the new buffer row and window row,
			# b) Unhighlight the old row.
			self.ibuff_idx = idx
			# rcol is report column (newspaper column)
			temp_rcol = int((idx - self.top_ibuff_idx) / w_height)
			# wcol is a character column for the window display
			temp_wcol = temp_rcol * (self.max_txt_width + 5 + SPACE_BETWEEN_COLUMNS)
			temp_wrow = (idx - self.top_ibuff_idx - temp_rcol * w_height)	
			self.frames[1].set_row(temp_wrow)
			self.frames[1].set_col(temp_wcol)
			
			self.frames[1].addstr(old_wrow \
				,old_wcol , str(old_ibuff_idx + 1) + ") " + self.ibuff[old_ibuff_idx],\
				curses.color_pair(self.formats[old_ibuff_idx]))
		else:
			# 3) Scroll if needed, and set ibuff_idx and the window row
			#    as was don for the non-scrolling case
			# Scrolling is needed
			if idx > old_ibuff_idx:
				# Scroll down (the cursor goes further down and continues down)
				# ASSUMES SCREEN HEIGHT IS AT LEAST 4!!!
				#
				if w_height < 4:
					# I should adjust the code below to scroll on short screens
					raise Exception("Cannot scroll when main display area " \
						+ "is less than 4 lines")

				# This will leave the cursor two rows above the bottom
				# of the right-most column
				self.ibuff_idx = idx
				self.top_ibuff_idx = idx -  self.report_cols * w_height + 3
				self.frames[1].set_row(w_height - 3)
				self.frames[1].set_col((self.report_cols - 1) * \
					(self.max_txt_width + 5 + SPACE_BETWEEN_COLUMNS))
			else:
				# Scroll up
				self.ibuff_idx = idx
				if idx > 1:
					self.top_ibuff_idx = idx - 1 
					self.frames[1].set_row(1)
					self.frames[1].set_col(0)
				else:
					self.top_ibuff_idx = 0 
					self.frames[1].set_row(idx)
					self.frames[1].set_col(0)
			# Redisplay the screen
			self.display_buff()
				
		# 4) For both the scrolling and non-scrolling conditions,
		#    highlight the new text line.
		self.frames[1].addstr(self.frames[1].get_row() \
				,self.frames[1].get_col() , str(self.ibuff_idx + 1) + \
				") " + self.ibuff[idx], curses.color_pair(\
				self.formats[self.frames[1].get_row()]) + curses.A_STANDOUT)
		self.frames[1].refresh()
		# note the full text of item name in the status bar
		self.frames[0].set_header_txt(2, self.ibuff[idx])
		self.frames[1].restore_cursor()
		return(0)

	def restore_screen(self):
		"""SelectionWindow.restore_screen()
		Fix the window attributes so that the screen will
		work properly when the user returns to the shell.
		"""	
		curses.nocbreak()
		curses.echo()
		curses.endwin()

	def cursorize_screen(self):
		"""SelectionWindow.cursorize_screen()
		Set window attributes so that they work well for 
		curses.
		"""	
		curses.cbreak()
		curses.noecho()

def list_files(path):
	"""list_files()
	This will list the entries in the specified directory
	and return two lists. The first list contains a code 
	for file (0) or directory (1) and the next contains
	the filenames or subdirectory names sorted with
	directories at the top.  The list will include
	an entry for ".." but not "."
	"""
	# Maybe I should explicitly remove directory "." in
	# case it appears in the listing on another platform.
	temp_file_names = os.listdir(path)
	os.chdir(path)
	l = []
	for s in temp_file_names:
		# get a directory flag
		flag = os.path.isdir(s)
		# set the display attribute for directories
		if flag:
			# the formats will be color curses color pairs
			l.append([1, s])
		else:
			l.append([0, s])
	q = sorted(l,key=lambda x:x[0], reverse=True)
	l = []
	fmt = []
	for o in q:
		l.append(o[1])
		fmt.append(o[0])
	# insert the .. directory to go up a directory
	l.insert(0, '..')
	fmt.insert(0, 1)
	return([l, fmt])

def portpath(pathL):
	"""portpath()
	Given a list object that contains ordered elements of a path 
	or path with filename, join those elements using
	the path separator and return the result.  This might improve
	portability across operating systems.

	Example:
	  portpath(["~","Documents", "myfile.txt"])
	"""
	return(os.path.normpath(os.path.expanduser(\
				os.path.sep.join(pathL))))

def load_options():
	"""load_options()
	Read ~/.dfconfig and load
	values from the [lgit] section into the global
	opts{} dictionary, and will also load some
	global variables.
	"""
	global g_opts
	global g_shortcuts
	global conf_file_portlist
	#
	default_options = []
	#
	# Load defaults into lgitcodes, which are options
	default_options.extend([
			["language", "Klingon"]]
	)
	#
	conf_file_name = portpath(conf_file_portlist)
	#
	if(os.access(conf_file_name, os.F_OK)):
		# Create a ConfigParser object:
		o = configparser.ConfigParser()
		#
		# Now read a list of config files (only one file)
		o.read([conf_file_name])
		#
		for sect in o.sections():
			# "sect" will contain something like "options" or
			# "shortcuts"
			g_opts.update({sect:{}})
			# Now process the option depending on option type:
			if sect=="defaults":	
				for m in default_options:
					# parms: configP object, sect, key, default
					my_get_opt(o, sect, m[0], m[1])
			else:
				# This runs for "shortcuts"
				for f in o.options(sect):
					my_get_opt(o, sect, f, "")
	else:
		print("The ~/.dfconfig configuration file was not found.")
		yn = yn_input("Do you want to initialize the options? (y/n) ")
		if(yn == "y"):
			setup()
#
def my_get_opt(confp, sect, optkey, default):
	"""my_get_opt()
	Load the requested options into the globally
	defined 'g_opts' dictionary. 
	'confp'   is a ConfigParser object.
	'sect'    is the options section code, such as 'defaults'\
						or 'shortcuts'.
	'optkey'  is the option within the specified section.
	'default' is the default value for this option.
	"""
	global g_opts
	global g_shortcuts
	#
	try:
		q = confp.get(sect, optkey)
	except configparser.NoOptionError:
		print("option not found in the " + sect + " section of the " 
					+ " config file: " + optkey + ". Using default: " + 
					repr(default))
		q = default
	#
	# Perform some translations for booleans:
	if(str(q).upper() in (["T", "TRUE", "Y", "YES"])):
		q = True
	elif(str(q).upper() in (["F", "FALSE", "N", "NO"])):
	   q = False
	elif(q.isdecimal()):
		q = int(q)
	#	
	### Ensure trailing slash on my directories:
	##if(optkey == "shortcuts":
	##	q = ensure_trailing_slash(q)
	#	

	##if(sect.find("-files") > 0):
	##	flist.update({optkey:[q, sect]})
	if sect == "shortcuts":
		g_shortcuts.update({optkey:q})
#
def main(stdscr):
	"""main()
	This will be called by curses.wrapper() so 
	that the program will exit properly.
	Be sure to use the stdscr that is sent to this function
	via the wrapper() function or else the keys won't work
	properly.
	"""	
	global g_selected_txt

	# Read command-line options
	# I AM NOT USING COMMAND LINE OPTION YET
	try:
		optlist, args = getopt.getopt(sys.argv[1:] \
			,"vh", ["verbose", "help"])
	except (getopt.GetoptError, err):
		print(str(err))
		usage()
		sys.exit(12)
	#
	for o, a in optlist:
		if (o in ("-h", "--help")):
			usage()
			sys.exit()
		elif (o in ("-v", "--verbose")):
			g_debug_level = 6

	#
	# Load options from ~/.dfconfig
	load_options()
	#
	stdscr.clear()
	curses.noecho()
	stdscr.keypad(1)#allos some escapekeys?
	curses.meta(1)# allow 8-bit characters
	#curses.start_color()# wrapper() should start color
	#
	#
	the_path = posix.getcwd()
	code = 1
	while code in [1, 2]:
		# A code of 1 means to list the new directory
		# and wait for the user to select a file
		# or directory.
		# A code of 2 means to open a shell at the
		# specified directory.
		(l, fmt) = list_files(the_path)
		# Instantiate the main object and then run it
		w = SelectionWindow(stdscr, 0, 1, l, fmt, the_path)
		(code, the_path) = w.key_loop()
	g_selected_txt = the_path

	# Returning a text value to curses.wrapper()
	# does nothing, so just return zero.
	return(0)

#
if __name__ == "__main__":
	# use the curses.wrapper() function to establish a 
	# curses window, detect mouse, and make the arrow
	# keys work correctly:
	curses.wrapper(main)
	# Return the selcted text from the global variable:
	print(g_selected_txt)
