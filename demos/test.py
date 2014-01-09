# -*- coding: utf-8 -*-

"""GLUT based SVG viewer."""


# imports ####################################################################

import sys
import os
import atexit
import glob
import traceback
import logging

from OpenGL.GLUT import *

from seagull import scenegraph as sg
from seagull.xml import parse, serialize
from seagull.opengl.utils import gl_prepare, gl_reshape, gl_display


# scene ######################################################################

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "contribs", "W3C_SVG_11_TestSuite", "svg")

def args(name, prefix="", path=DEFAULT_PATH):
	return name, prefix, path
try:
	_, prefix, test_path = args(*sys.argv)
except:
	raise RuntimeError("missing or too much args")

old_cwd = os.getcwd()
os.chdir(test_path)
atexit.register(os.chdir, old_cwd)

SKIP_LIST = ["animate-", "dom-"]
filenames = [
	f for f in glob.glob("%s*.svg*" % prefix)
	if not any(skip in f for skip in SKIP_LIST)
]
current = 0

def load(index):
	global scene, image
	filename = filenames[index]
	t = "[%3i+1/%i] %s" % (index, len(filenames), filename)
	glutSetWindowTitle(t.encode())
	print(t)
	try:
		if filename.endswith('z'):
			import gzip
			f = gzip.open(filename)
		else:
			f = open(filename)
		svg = parse(f.read(), logging.WARNING)
	except:
		traceback.print_exception(*sys.exc_info())
		svg = sg.Group()
	image = sg.Image("../png/%s.png" % filename.rsplit(".", 1)[0], x=480)
	scene = sg.Group(
		children=[svg, image],
	)
	
	(x_min, y_min), (x_max, y_max) = scene.aabbox()
	glutReshapeWindow(int(x_max), int(y_max))
	glutPostRedisplay()
	return index


def goto(index):
	global current
	current = index % len(filenames)
	return load(current)

def next_file():
	return goto(current+1)

def prev_file():
	return goto(current-1)


# glut callbacks #############################################################

def display():
	gl_display(scene)
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

def special(k, x, y):
	if k == GLUT_KEY_RIGHT:
		next_file()
	elif k == GLUT_KEY_LEFT:
		prev_file()


# main #######################################################################

glutInit(sys.argv)

glutInitDisplayString(b"rgba stencil double samples=16 hidpi")
glutCreateWindow(sys.argv[0].encode())

glutReshapeFunc(gl_reshape)
glutDisplayFunc(display)

glutKeyboardFunc(keyboard)
glutSpecialFunc(special)

menus = {
	(): glutCreateMenu(goto),
}
glutAttachMenu(GLUT_RIGHT_BUTTON)

for i, name in enumerate(filenames):
	path = tuple(n.encode() for n in name.split("-")[:-1])
	for j in range(len(path)):
		k = path[:j]
		try:
			menu = menus[k]
		except KeyError:
			submenu = glutCreateMenu(goto)
			glutSetMenu(menu)
			glutAddSubMenu(k[-1], submenu)
			menu = menus[k] = submenu
	glutSetMenu(menu)
	glutAddMenuEntry(path[-1], i)


gl_prepare()

load(current)

glutMainLoop()
