# -*- coding: utf-8 -*-

"""GLUT based SVG viewer."""


# imports ####################################################################

import sys
import os
import atexit
import glob
import traceback

from OpenGL.GLUT import *

from seagull import scenegraph as sg
from seagull.xml import parse, serialize
from seagull.opengl.utils import gl_prepare, gl_reshape, gl_display


# scene ######################################################################

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "contribs", "W3C_SVG_11_TestSuite", "svg")

def args(name, current=0, path=DEFAULT_PATH):
	return name, int(current), path
try:
	_, current, test_path = args(*sys.argv)
except:
	raise RuntimeError("missing or too much args")

old_cwd = os.getcwd()
os.chdir(test_path)
atexit.register(os.chdir, old_cwd)

filenames = glob.glob("*.svg")

def load(index):
	global scene, image
	filename = filenames[index]
	t = "[%3i/%i] %s" % (index+1, len(filenames), filename)
	glutSetWindowTitle(t.encode())
	print(t)
	try:
		scene = parse(open(filename).read())
	except:
		traceback.print_exception(*sys.exc_info())
		scene = sg.Group()
	image = sg.Image("../png/%s.png" % filename[:-4], x=480)
	
def goto(index):
	global current
	current = index % len(filenames)
	load(current)

def next_file():
	goto(current+1)
	
def prev_file():
	goto(current-1)


# glut callbacks #############################################################

def display():
	gl_display(scene, image)
	glutSwapBuffers()


# interation #################################################################

def keyboard(c, x, y):
	if c == b'q':
		sys.exit(0)
	elif c == b's':
		sys.stdout.write(serialize(scene))		
	elif c == b']':
		next_file()
	elif c == b'[':
		prev_file()
	
	glutPostRedisplay()


# main #######################################################################

glutInit(sys.argv)

glutInitDisplayString(b"rgba stencil double samples=4")
glutInitWindowSize(480*2, 360)
glutCreateWindow(sys.argv[0].encode())

glutReshapeFunc(gl_reshape)
glutDisplayFunc(display)

glutKeyboardFunc(keyboard)

gl_prepare()

load(current)

glutMainLoop()
