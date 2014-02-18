# -*- coding: utf-8 -*-

"""GLUT based SVG viewer."""


# imports ####################################################################

import sys

from math import exp

import OpenGL
OpenGL.ERROR_CHECKING = False
OpenGL.CONTEXT_CHECKING = False # the doc lies: default value is True
OpenGL.ARRAY_SIZE_CHECKING = False

from OpenGL.GLUT import *

from seagull import scenegraph as sg
from seagull.scenegraph.transform import product, normalized
from seagull.xml import parse, serialize
from seagull.opengl.utils import gl_prepare, gl_reshape, gl_display


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


# glut callbacks #############################################################

def display():
	gl_display(scene, feedback)
	glutSwapBuffers()


# interation #################################################################

IDLE, DRAGGING, ROTATING, ZOOMING = range(4)
state = IDLE

def mouse(button, event, x, y):
	global state, origin, x0, y0
	if event == GLUT_DOWN:
		if button == GLUT_LEFT_BUTTON:
			state = DRAGGING
		elif button == GLUT_MIDDLE_BUTTON:
			state = ROTATING
		elif button == GLUT_RIGHT_BUTTON:
			state = ZOOMING
	else:
		state = IDLE
	origin = x0, y0 = x, y


def motion(x1, y1):
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
	glutPostRedisplay()


def keyboard(c, x, y):
	if c == b'q':
		sys.exit(0)
	elif c == b's':
		sys.stdout.write(serialize(scene))
	glutPostRedisplay()


# main #######################################################################

glutInit(sys.argv)

glutInitDisplayString(b"rgba stencil double samples=16 hidpi")
glutInitWindowSize(*window_size)
glutCreateWindow(sys.argv[0].encode())

glutReshapeFunc(gl_reshape)
glutDisplayFunc(display)

glutMouseFunc(mouse)
glutMotionFunc(motion)
glutPassiveMotionFunc(motion)
glutKeyboardFunc(keyboard)

gl_prepare()

glutMainLoop()
