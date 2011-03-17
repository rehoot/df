#!/usr/bin/python
#
"""
df.py version 0.01 for python 2.6
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

df.py is a "(pseudo) menu"-driven program that will list
subdirectories in the current directory and allow the
user to navigate by entering the numbers that correspond
to the directories in the list.  A better implementation
might use the curses library.


Instructions:
1) run this script and enter numbers to select the directory that
   you want to view.  Option 1 will typically go to the parent
   directory.
2) I hard-coded some shortcuts that are listed near the bottom
   of the screen.  You can change those by editing this python
   script.
3) You can run a shell command from the currently-selected
   directory by entering something like:
   !ls -l
   where the "!" is the code that the rest of the line is a shell
   command.
4) If you select option G for "goto," this program will attempt
   to invoke a new shell and go to the selected directory.
   this program will exit after you type "exit" in the new subshell
   and you will return to the old shell prompt were you started
   this python script.


"""
#
#
import sys, os,re, subprocess, getopt, posix, pty
SHELL_PGM="/bin/bash"
rptcols = 1
MENU_ROW_CT = 4
#
#
def usage():
	print("usage:")
	print("df.py [-h] [-v] [-i]")
	print("    -h = --help")
	print("    -v = --verbose")
	print("    -i = --include-dot-files")
	sys.exit(0)
#
#
def main():
	try:
		optlist, args = getopt.getopt(sys.argv[1:],
			"hvi", ["help", "verbose", "include-dot-files"])
	except getopt.GetoptError, err:
		print(str(err))
		usage()
		sys.exit(12)

	b_include = False #include dot files?
	for o, a in optlist:
		if(o in ["-i", "--include-dot-files"]):
			b_include = True
		elif (o in ["-v", "--verbose"]):
			# doesn't do anything right now
			pass
		elif (o in ["-h", "--help"]):
			usage()
		else:
			print("Error. Bad option: " + o + " and " + a)
			sys.exit(12)

	newdir = "./"
	savedir = posix.getcwd()
	while(type(newdir) == type(str())):
		newdir = get_and_list_files(b_include)
		if(type(newdir) == type(str())):
			os.chdir(newdir)
			savedir = newdir
	
	# Now the desired directory name is stored in "savedir."
	# Open a terminal here.
	#
	# There is a trick to doing this because if I issue a regular
	# cd command, the directory will change only within the 
	# subshell that runs this script.  When I exit, I'll be 
	# in the same diretory where I started.  From a regular
	# shell script, you can run it with a ". " prefix and the
	# script will run in the current shell, but that doesn't
	# work with python.  I used the subprocess.communicate()
	# feature to tell the new subshell to change the directory.
	#
	myenv={"HOME": savedir}
	os.putenv("HOME", savedir)
	p1 = subprocess.Popen([SHELL_PGM, "-is"], stdin=sys.stdin, stdout=sys.stdout)
	p1.communicate("cd " + savedir)
	return(savedir)

def get_and_list_files(b_include):
	# Issue the find command and capture the resulting list
	# of directories (no regular files--I'm not sure about
	# linked directories).
	results = []

	cmdlist = ["find", "./", "-maxdepth", "1", "-type", "d"]

	if b_include == False:
		cmdlist.extend(["-not", "-name", ".*"])
	filelist = subprocess.Popen(cmdlist,
		stdout=subprocess.PIPE).communicate()[0]
	#
	# Append numbers to the display text:
	j = 1
	results = filelist.split("\n")
	removevals = [" ", "\n", ""]
	for s in removevals:
		# remove a list entry if the full value
		# is exctly equal to a space or a newline
		try:
			results.remove(s)
		except ValueError:
			pass
	os.putenv("PS1","$USER:$PWD > ")
	#
	# Add the code for the directory above
	results.insert(0,"..")
	return(list_dir(results))

def list_dir(masterlist):
	# Use the global value for 'masterlist' to list
	# directory (or file) names and their index
	# numbers, prompt for a selection from this list
	# and return the string value for that selection
	# This will return the filename or int(-2) if
	# the user chooses option G

	global rptcols

	rpttmp = []
	# First get the number of screen rows so I can
	# try to format the output (limit the number of rows
	cmdlist1 = ("/bin/stty size")
	cmdlist2 = ("/usr/bin/awk", "{print($1)}")
	tty_stats = subprocess.Popen(cmdlist1,shell=True,
		stdout=subprocess.PIPE)
	tty_rows = int(subprocess.Popen(cmdlist2,
		stdout=subprocess.PIPE,
		stdin=tty_stats.stdout).communicate()[0])
	#print("screen rows" + str(tty_rows))

	# Number the directory names and put them into rpttmp
	j = 1
	for s in masterlist:
		if(s != ""):
			#print(str(j) + ")" + s + ".")
			rpttmp.append(str(j) + ")" + s)
		j = j + 1
	rptcols = 1
	if(len(rpttmp) > (tty_rows - MENU_ROW_CT)):
		rptcols = int(len(rpttmp) / (tty_rows - MENU_ROW_CT)) + 1
	if(rptcols > 5):
		rptcols = 5
	rptrows = int(len(rpttmp) / rptcols) + 1
	#
	# Initialize with a list that has the specified
	# number of columns.  The first entry in that 
	# list will expand into the first column...
	# WARNING: THE OLD INITIALIZATION FOR RPTOUT SEEMED
	# TO CAUSE LATER CODE TO SEND .APPEND TO ALL THREE COLLUMNS.
	#rptout = [[" "]] * rptcols
	#rptout = [[],[],[]] # this was OK but not dynamic
	rptout = [[]]
	for j in range(rptcols - 1 ):
		rptout.append([])
	r = 0
	k = 0
	for j in range(len(rpttmp)):
		rptout[k].append(rpttmp[j])
		r += 1
		if(r >= rptrows):
			r = 0
			k += 1

	# the last record might need some blanks so that it has
	# the correct number of columns.
	k = 0
	while( len(rptout[rptcols - 1]) < rptrows):
		rptout[rptcols - 1].extend(" ")
	print("before output, cols are " + str(rptcols))
	if(rptcols > 1):
		format_columns(rptout, rowsepchar="", colmax=[38])
	else:	
		for s in rpttmp:
			print(s )
		print("")
	for j in range(tty_rows - len(rptout[0]) - MENU_ROW_CT):
		# print blank rows to clear the sreen
		print("")
			
	print("    $ " + posix.getcwd())
	print("D = Diss, E = eBooks, P = python, R, U = unix")
	print("Q = quit, ~ = home, G = Goto dir, ! = Shell cmd")
	# Do not convert the input to caps because I might enter
	# the full shell command here
	strnbr = raw_input("Enter a directory number: ")
	if (strnbr.upper() == "Q"):
		print("quitting")
		sys.exit(0)
	elif (strnbr == "~"):
		print("IN THE TILDE CODE")
		newdir = os.path.realpath(os.path.expanduser("~/"))
		return(newdir)
	elif (strnbr.upper() == "D"):
		newdir = os.path.realpath(os.path.expanduser("/Volumes/D/Documents/Walden/PhD/Dissertation"))
		return(newdir)
	elif (strnbr.upper() == "E"):
		newdir = os.path.realpath(os.path.expanduser("/Volumes/D/Documents/eBooks"))
		return(newdir)
	elif (strnbr.upper() == "P"):
		newdir = os.path.realpath(os.path.expanduser("/py"))
		return(newdir)
	elif (strnbr.upper() == "R"):
		newdir = os.path.realpath(os.path.expanduser("/Volumes/D/Documents/unix/R"))
		return(newdir)
	elif (strnbr.upper() == "U"):
		newdir = os.path.realpath(os.path.expanduser("/Volumes/D/Documents/unix"))
		return(newdir)
	elif (strnbr == "!" or strnbr[0]=="!"):
		# Shell command
		if(len(strnbr)==1):
			cmdstr = raw_input("Enter your shell command: ")
		else:
			cmdstr = strnbr[1:]
		cmdlst = cmdstr.split(" ")	
		## My stty command worked only in string mode
		## not list mode for Popen:
		#rslt = subprocess.Popen(cmdstr, 
		#	stdout=subprocess.PIPE).communicate()[0]
		os.system(cmdstr)
		junk = raw_input("Press enter to continue")
		newdir = posix.getcwd()
		return(newdir)
	elif (strnbr.upper() == "G"):
		return(-13)
	elif (not(strnbr.isdigit())):
		print("Entry not valid.")
		sys.exit(4)
	elif(int(strnbr) > (len(masterlist))):
		print("Entry not a valid number.")
		sys.exit(-1)
	else:
		newdir = os.path.realpath(masterlist[int(strnbr)-1])
		return(newdir)
#
#

def demo():
	# do not hack this because it will be called during the 
	# ArchiveDitto.py synchronization.
	find(sys.argv[1:])


def format_columns(rpt,padwidth=2,colmax=[25,100],rowsepchar="-"):
	"""Read a list object called rpt[] that contains at least two
	additional lists that represent data for the columns of a report.
	Each of the two or more entries in rpt[] should have the same number
	of elements in which each element represents a line of text.  The
	padwith setting controls the number of blank spaces between columns.
	You can override the colmax[] list by providing the maximum column widht
	for each column.  If colmax has fewer elements than there are columns,
	then the last element will be repeated for the remaining columns. If
	the text is substantially less than the max amount, they will be shrunk
	accordingly"""
	
	num_cols = len(rpt)
	num_rows = len(rpt[0])
	# Extend the column max widths if needed
	while num_cols > len(colmax):
		colmax.append(colmax[-1])
	#
	# txt_widths is the max width for each column
	txt_widths = [0]*num_cols
	for j in range(num_rows):
		# Initialize the width of each column before scanning text.
		for k in range(num_cols):
			if len(rpt[k][j]) > txt_widths[k]:
				# Save the width of this row for this column as the new max
				txt_widths[k] =  len(rpt[k][j])
	#
	# If one or more of the columns were extra skinny, shrink the column
	rpt_width = padwidth * (num_cols - 1)
	for k in range(num_cols):
		if txt_widths[k] < colmax[k]:
			colmax[k] = txt_widths[k]
		rpt_width += colmax[k]
	#
	
	max_subrows = [1]*num_rows
	for j in range(num_rows):
		# For each row...
		output = ""
		tmp_subrows=[]
		#
		for k in range(num_cols):
			# For each column...
			# Calculate the number of subrows based on the word wrap
			# that will fit into each max column width.
						# 1 = one output row per input line ?
			tmp = int(len(rpt[k][j]) / colmax[k]) 
			if tmp > max_subrows[j]:
				max_subrows[j] = tmp
		#
		for k in range(num_cols):
			tmp_subrows.append(rpt[k][j].ljust(colmax[k]*(max_subrows[j])))
		for l in range(max_subrows[j]):
			for k in range(num_cols):
				# for each subrow (i.e. the text might be too wide and might
				# need to be split across several rows)
				output += str(tmp_subrows[k][l*colmax[k]:(l+1)*colmax[k]])
				if k < (num_cols - 1):
										# print the column delimiter
					output += " "*padwidth
			if l < (max_subrows[j] - 1):
				output += "\n"  
		print (output   )
		if rowsepchar != "":
			print (rowsepchar*rpt_width)


if __name__ == '__main__':
	main()
	#demo()


