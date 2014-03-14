# -*- coding: utf-8 -*-

"""Qt5 based SVG viewer."""


# imports ####################################################################

import sys
import os

from math import exp

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtOpenGL import QGL, QGLFormat, QGLWidget

from seagull import scenegraph as sg
from seagull.scenegraph.transform import product, normalized
from seagull.xml import parse, serialize
from seagull.opengl.utils import gl_prepare, gl_reshape, gl_displayer


# scene ######################################################################

try:
	_, filename = sys.argv
except:
	raise RuntimeError("missing or too much args")

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

IDLE, DRAGGING, ROTATING, ZOOMING = range(4)
state = IDLE

def xy(event):
	return tuple(u*window.devicePixelRatio() for u in (event.x(), event.y()))

def mouse_press(event):
	global state, origin, x0, y0
	x, y = xy(event)
	if event.buttons() & Qt.LeftButton:
		state = DRAGGING
	elif event.buttons() & Qt.MidButton:
		state = ROTATING
	elif event.buttons() & Qt.RightButton:
		state = ZOOMING
	origin = x0, y0 = x, y

def mouse_release(event):
	global state
	state = IDLE


def mouse_move(event):
	global x0, y0
	x1, y1 = xy(event)
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
	window.updateGL()


# main #######################################################################

app = QApplication(sys.argv)
window = QGLWidget(QGLFormat(QGL.SampleBuffers))
window.setWindowTitle(sys.argv[0])
window.resize(*(u/window.devicePixelRatio() for u in window_size))
window.initializeGL = gl_prepare
window.resizeGL = gl_reshape
window.paintGL = gl_displayer(scene, feedback)
window.mousePressEvent = mouse_press
window.mouseReleaseEvent = mouse_release
window.mouseMoveEvent = mouse_move
window.setMouseTracking(True)
window.show()
sys.exit(app.exec_())
