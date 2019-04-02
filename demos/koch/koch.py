#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""SVG using seagull API."""


# imports ####################################################################

import os
import sys

this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(this_dir, '../..'))

from OpenGL.GLUT import *

from seagull import scenegraph as sg
from seagull.xml.serializer import serialize
from seagull.opengl.utils import gl_prepare, gl_reshape, gl_displayer


# scene ######################################################################

def _koch(n, k0):
	if n <= 1:
		return k0
	kp = _koch(n-1, k0)
	return sg.Group(children=[
		sg.Use(kp, transform=t)
		for t in [
			[sg.Scale(1/3)],
			[sg.Scale(1/3), sg.Translate(100), sg.Rotate(-60)],
			[sg.Scale(1/3), sg.Translate(200), sg.Rotate(-120), sg.Scale(1, -1)],
			[sg.Scale(1/3), sg.Translate(200)],
		]
	])

def koch(n, k0=sg.Line(x2=100)):
	return sg.Group(
		transform=[sg.Scale(10), sg.Translate(10, 40)],
		stroke=sg.Color.black,
		stroke_width=.05*3**n,
		stroke_linecap="round",
		children=[_koch(n, k0)],
	)

n = 6
scene = sg.Group(children=[koch(n)])


# glut callbacks #############################################################

def keyboard(c, x, y):
	if c == b'q':
		sys.exit(0)
	elif c in b'+-':
		global n
		if c == b'+':
			n += 1
		else:
			n -= 1
		scene.children = [koch(n)]
	elif c == b's':
		sys.stdout.write(serialize(scene))
	glutPostRedisplay()


# main #######################################################################

glutInit(sys.argv)

glutInitDisplayString(b"rgba stencil double samples=8 hidpi core")
glutInitWindowSize(1200, 500)
glutCreateWindow(sys.argv[0].encode())


glutReshapeFunc(gl_reshape)
glutDisplayFunc(gl_displayer(scene, swap_buffers=glutSwapBuffers))
gl_prepare()

glutKeyboardFunc(keyboard)

glutMainLoop()
