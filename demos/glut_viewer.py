# -*- coding: utf-8 -*-

"""GLUT based SVG viewer."""


# imports ####################################################################

import sys

from math import exp

from OpenGL.GLUT import *

from seagull import scenegraph as sg
from seagull.gl_utils import gl_prepare, gl_reshape, gl_display
from seagull.svg import parse, serialize


# scene ######################################################################

scene = sg.Group()

blue2green = sg.LinearGradient(stops=[(0., sg.Color.blue), (1., sg.Color.green)])
white2black = sg.LinearGradient(stops=[(.2, sg.Color.black), (.8, sg.Color.white)])

rectangle = sg.Rectangle(x=10, y=10, rx=15, ry=15, width=100, height=100,
                         fill=sg.RadialGradient(blue2green, fx=0., fy=.5),
                         transform=[sg.Rotate(30), sg.Scale(1.5)])

path = sg.Path(d=['M', (0, 0), 'C', (200,  200), (-200,  200), (0, 0),
                               'C', (200, -200), (-200, -200), (0, 0), 'Z'],
               fill=sg.LinearGradient(white2black, x2=1., y2=.5),
               stroke=sg.Color.black, stroke_width=6)

arcs = sg.Group(stroke=sg.Color.blue, stroke_width=5, children=[
	sg.Path(d=['M', (300, 200), 'L', (150, 200),
	           'A', (150, 150), 0, (1, 0), (300, 50), 'Z'],
	        fill=sg.Color.red),
	sg.Path(d=['M', (275, 175), 'L', (275, 25),
	           'A', (150, 150), 0, (0, 0), (125, 175), 'Z'],
	        fill=sg.Color.yellow),
	sg.Path(d=['M', (600, 350), 'l', (50, -25),
	           'a', (25, 25),  -30, (0, 1), (50, -25), 'l', (50, -25),
	           'a', (25, 50),  -30, (0, 1), (50, -25), 'l', (50, -25),
	           'a', (25, 75),  -30, (0, 1), (50, -25), 'l', (50, -25),
	           'a', (25, 100), -30, (0, 1), (50, -25), 'l', (50, -25),],
	        fill=None, stroke=sg.Color.red)
])

circle = sg.Circle(cx=20, cy=20, r=50,
                   fill=sg.Color.purple, fill_opacity=.5,
                   stroke=sg.Color.green, stroke_width=8)

ellipse = sg.Ellipse(cx=100, cy=-80, rx=60, ry=30,
                     fill=sg.Color.fuchsia, fill_opacity=.5,
                     stroke=sg.Color.teal, stroke_width=4)

line = sg.Line(x1=100, y1=300, x2=300, y2=100,
               stroke=sg.Color.green, stroke_width=5)

polyline = sg.Polyline(stroke=sg.Color.blue, stroke_width=10, fill=None,
                       points=[(50,375), (150,375), (150,325), (250,325), (250,375),
                               (350,375), (350,250), (450,250), (450,375),
                               (550,375), (550,175), (650,175), (650,375),
                               (750,375), (750,100), (850,100), (850,375),
                               (950,375), (950,25), (1050,25), (1050,375), (1150,375)])

polygon = sg.Polygon(fill=sg.Color.red, stroke=sg.Color.blue, stroke_width=10,
                     points=[(350,75), (379,161), (469,161), (397,215),
                             (423,301), (350,250), (277,301), (303,215),
                             (231,161), (321,161)])


if len(sys.argv) == 1:
	group = sg.Group(children=[rectangle, path, arcs,
	                           circle, ellipse, line, polyline, polygon])
else:
	group = sg.Group()
	for filename in sys.argv[1:]:
		document = open(filename).read()
		old_cwd = os.getcwd()
		os.chdir(os.path.dirname(filename))
		group.children.append(parse(document))
		os.chdir(old_cwd)

scene.children.append(group)
scene.children.append(sg.Use(group, transform=[sg.Translate(200, 150), sg.Scale(.5), sg.Rotate(60)]))


# glut callbacks #############################################################

def display():
	gl_display(scene)
	glutSwapBuffers()


# interation #################################################################

def pick(x, y):
	for path, point in reversed(scene.pick(x, y)):
		return path
	return [scene, group]

def project(path, x, y, z=0):
	for elem in path:
		x, y, z = elem.project(x, y, z)
	return x, y


IDLE, DRAGGING, ZOOMING = range(3)
state = IDLE

def mouse(button, event, x, y):
	global state, path, origin, x0, y0
	if event == GLUT_DOWN:
		path = pick(x, y)
		if button == GLUT_LEFT_BUTTON:
			state = DRAGGING
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
		transformation = [sg.Translate(px-ox, py-oy)]

	elif state == ZOOMING:
		ds = exp(((x1-x0)-(y1-y0))*.01)
		ox, oy = project(path, *origin)
		transformation = [
			sg.Translate((1-ds)*ox, (1-ds)*oy),
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

glutInitDisplayString(b"rgba stencil double samples=4")
glutCreateWindow(sys.argv[0].encode())

glutReshapeFunc(gl_reshape)
glutDisplayFunc(display)

glutMouseFunc(mouse)
glutMotionFunc(motion)
glutKeyboardFunc(keyboard)

gl_prepare()

glutMainLoop()
