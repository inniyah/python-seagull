# -*- coding: utf-8 -*-

"""GLUT based SVG viewer."""


# imports ####################################################################

import sys

from math import exp

from OpenGL.GLUT import *

from seagull import scenegraph as sg
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
with open(filename) as f:
	scene = parse(f.read())
os.chdir(old_cwd)

(x_min, y_min), (x_max, y_max) = scene.aabbox()
margin = 20
scene.transform.append(sg.Translate(margin-x_min, margin-y_min))


# glut callbacks #############################################################

def display():
	gl_display(scene)
	glutSwapBuffers()


# interation #################################################################

def pick(x, y):
	for path, point in reversed(scene.pick(x, y)):
		return path
	return [scene]

def project(path, x, y, z=0):
	for elem in path:
		x, y, z = elem.project(x, y, z)
	return x, y


IDLE, DRAGGING, ROTATING, ZOOMING = range(4)
state = IDLE

def mouse(button, event, x, y):
	global state, path, origin, x0, y0
	if event == GLUT_DOWN:
		path = pick(x, y)
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
	global state, path, origin, x0, y0

	if state == DRAGGING:
		ox, oy = project(path, x0, y0)
		px, py = project(path, x1, y1)
		transformation = [
			sg.Translate(px-ox, py-oy)
		]

	elif state == ROTATING:
		a = (x1-x0)-(y1-y0)
		x, y = project(path, *origin)
		transformation = [
			sg.Rotate(a, x, y),
		]

	elif state == ZOOMING:
		ds = exp(((x1-x0)-(y1-y0))*.01)
		x, y = project(path, *origin)
		transformation = [
			sg.Translate((1-ds)*x, (1-ds)*y),
			sg.Scale(ds),
		]
	
	else:
		raise RuntimeError("Unexpected interaction state '%s'" % state)
	
	elem = path[-1]
	elem.transform += transformation
	elem.transform = elem.transform.normalized()
	
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

glutInitDisplayString(b"rgba stencil double samples=8")
glutInitWindowSize(int(x_max-x_min+2*margin), int(y_max-y_min+2*margin))
glutCreateWindow(sys.argv[0].encode())

glutReshapeFunc(gl_reshape)
glutDisplayFunc(display)

glutMouseFunc(mouse)
glutMotionFunc(motion)
glutKeyboardFunc(keyboard)

gl_prepare()

glutMainLoop()
