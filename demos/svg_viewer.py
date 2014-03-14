#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""SVG viewer."""


# handling args ##############################################################

import sys
import getopt
import textwrap

name, args = sys.argv[0], sys.argv[1:]

DEFAULTS = {
	"debug":  False,
	"toolkit": "glut",
}

def exit_usage(message=None, code=0):
	usage = textwrap.dedent("""\
	Usage: %(name)s [-hdt:] <doc.svg>
		-h --help               print this help message then exit
		-d --debug              enable gl error checking
		-t --toolkit [glut|qt]  choose toolkit (defaults to %(toolkit)r)
		<doc.svg>               file to show
	""" % dict(name=name, **DEFAULTS))
	if message:
		sys.stderr.write("%s\n" % message)
	sys.stderr.write(usage)
	sys.exit(code)

try:
	options, args = getopt.getopt(args, "ht:", ["help"])
except getopt.GetoptError as message:
	exit_usage(message, 1)


# options

error_checking = DEFAULTS["debug"]
toolkit        = DEFAULTS["toolkit"]

for opt, value in options:
	if opt in ["-h", "--help"]:
		exit_usage()
	elif opt in ["-d", "--debug"]:
		error_checking = True
	elif opt in ["-t", "--toolkit"]:
		toolkit = value
		if toolkit not in ["glut", "qt"]:
			exit_usage("toolkit should be one of [glut|qt]", 1)

if not error_checking:
	import OpenGL
	OpenGL.ERROR_CHECKING = False
	OpenGL.ERROR_ON_COPY = True
	OpenGL.STORE_POINTERS = False

# argument

try:
	filename, = args
except:
	exit_usage("a single file name should be provided", 1)


# scene ######################################################################

import os

from seagull import scenegraph as sg
from seagull.scenegraph.transform import product, normalized
from seagull.xml import parse, serialize
from seagull.opengl.utils import gl_prepare, gl_reshape, gl_displayer

old_cwd = os.getcwd()
path, filename = os.path.split(filename)
if path:
	os.chdir(path)
if filename.endswith('z'):
	import gzip
	f = gzip.open(filename)
else:
	f = open(filename)
svg = parse(f.read())
f.close()

os.chdir(old_cwd)

(x_min, y_min), (x_max, y_max) = svg.aabbox()
margin = 20
window_size = int(x_max-x_min+2*margin), int(y_max-y_min+2*margin)

scene = sg.Use(svg, transform=[sg.Translate(margin-x_min, margin-y_min)])
feedback = sg.Group(fill=None, stroke=sg.Color.red)


# interaction ################################################################

from math import exp

LEFT, MIDDLE, RIGHT = range(3)
IDLE, DRAGGING, ROTATING, ZOOMING = range(4)
state = IDLE

def press(button, x, y):
	global state, origin, x0, y0
	if button == LEFT:
		state = DRAGGING
	elif button == RIGHT:
		state = ROTATING
	elif button == MIDDLE:
		state = ZOOMING
	origin = x0, y0 = x, y

def release():
	global state
	state = IDLE

def move(x1, y1):
	global x0, y0
	
	feedback.children = []
	if state == IDLE:
		for path, point in scene.pick(x1, y1):
			transform = product(*(elem.matrix() for elem in path[:-1]))
			(x_min, y_min), (x_max, y_max) = path[-1].aabbox(transform)
			feedback.children.append(sg.Rectangle(x=x_min, y=y_min,
			                                      width=x_max-x_min, height=y_max-y_min))
			x, y = point
			feedback.children.append(sg.Rectangle(
				x=x-3, y=y-3, width=5, height=5,
				transform = sum((elem.transform + [sg.Translate(elem.x, elem.y)] for elem in path), [])
			))
	
	elif state == DRAGGING:
		scene.transform = [sg.Translate(x1-x0, y1-y0)] + scene.transform
	
	elif state == ROTATING:
		scene.transform = [sg.Rotate((x1-x0)-(y1-y0), *origin)] + scene.transform
	
	elif state == ZOOMING:
		ds = exp(((x1-x0)-(y1-y0))*.01)
		x, y = origin
		scene.transform = [sg.Translate((1-ds)*x, (1-ds)*y), sg.Scale(ds)] + scene.transform
	
	else:
		raise RuntimeError("Unexpected interaction state '%s'" % state)

	scene.transform = normalized(scene.transform)
	x0, y0 = x1, y1
	post_redisplay()


def keyboard(c, x, y):
	if c == b'q':
		sys.exit(0)
	elif c == b's':
		sys.stdout.write(serialize(scene))
	post_redisplay()


# main #######################################################################

"""toolkit dependent code"""

if toolkit == "glut":
	from OpenGL.GLUT import *

	glutInit(sys.argv)

	glutInitDisplayString(b"rgba stencil double samples=16 hidpi core")
	glutInitWindowSize(*window_size)
	glutCreateWindow(name.encode())
	
	display = gl_displayer(scene, feedback)
	def display_func():
		display()
		glutSwapBuffers()
	
	BUTTONS = {
		GLUT_LEFT_BUTTON:   LEFT,
		GLUT_MIDDLE_BUTTON: MIDDLE,
		GLUT_RIGHT_BUTTON:  RIGHT,
	}
	
	def mouse_func(button, state, x, y):
		if state == GLUT_DOWN:
			press(BUTTONS[button], x, y)
		elif state == GLUT_UP:
			release()

	motion_func = move
	post_redisplay = glutPostRedisplay

	gl_prepare()
	glutReshapeFunc(gl_reshape)
	glutDisplayFunc(display_func)

	glutMouseFunc(mouse_func)
	glutMotionFunc(motion_func)
	glutPassiveMotionFunc(motion_func)
	glutKeyboardFunc(keyboard)

	glutMainLoop()


elif toolkit == "qt":
	from PyQt5.QtCore import Qt
	from PyQt5.QtWidgets import QApplication
	from PyQt5.QtOpenGL import QGL, QGLFormat, QGLWidget

	app = QApplication(sys.argv)
	window = QGLWidget(QGLFormat(QGL.SampleBuffers))
	pixel_ratio = window.devicePixelRatio()
	window.resize(*(u/pixel_ratio for u in window_size))
	window.setWindowTitle(name)
	

	def xy(event):
		return tuple(u*pixel_ratio for u in (event.x(), event.y()))

	def mouse_press(event):
		if event.buttons() & Qt.LeftButton:
			button = LEFT
		elif event.buttons() & Qt.MidButton:
			button = MIDDLE
		elif event.buttons() & Qt.RightButton:
			button = RIGHT
		press(button, *xy(event))

	def mouse_release(event):
		release()
	
	def wheel(event):
		x, y = xy(event)
		press(MIDDLE, x, y)
		delta = event.angleDelta()
		move(x+delta.x(), y+delta.y())
		release()
		
	def mouse_move(event):
		move(*xy(event))
		event.accept()

	post_redisplay = window.updateGL
		
	window.initializeGL = gl_prepare
	window.resizeGL = gl_reshape
	window.paintGL = gl_displayer(scene, feedback)
	window.mousePressEvent = mouse_press
	window.mouseReleaseEvent = mouse_release
	window.mouseMoveEvent = mouse_move
	window.wheelEvent = wheel
	window.setMouseTracking(True)
	
	window.show()
	sys.exit(app.exec_())
