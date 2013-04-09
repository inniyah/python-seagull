# -*- coding: utf-8 -*-

"""GLUT based SVG viewer."""


# imports ####################################################################

import sys

from OpenGL.GLUT import *

from seagull import scenegraph as sg
from seagull.gl_utils import gl_prepare, gl_reshape, gl_display


# glut callbacks #############################################################

def display():
	gl_display()
	glutSwapBuffers()

def keyboard(c, x, y):
	if c == b'q':
		sys.exit(0)
	glutPostRedisplay()

	
# main #######################################################################

glutInit(sys.argv)

glutInitDisplayMode(GLUT_RGBA|GLUT_STENCIL|GLUT_DOUBLE)
glutCreateWindow(sys.argv[0].encode())

glutReshapeFunc(gl_reshape)
glutDisplayFunc(display)

glutKeyboardFunc(keyboard)

gl_prepare()

glutMainLoop()
