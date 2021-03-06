#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""SVG viewer."""

import os
import sys

this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(this_dir, '..', '..'))

# handling args ##############################################################

import getopt
import textwrap

name, args = sys.argv[0], sys.argv[1:]

DEFAULTS = {
	"core":    False,
	"fast":    False,
	"time":    False,
	"profile": False,
	"toolkit": "glut",
	"margin":  20,
}

def exit_usage(message=None, code=0):
	usage = textwrap.dedent("""\
	Usage: %(name)s [-hftpk:m:] <doc.svg>
		-h --help                       print this help message then exit
		-c --core                       enable gl core profile use
		-f --fast                       disable gl error checking
		-t --time                       time gl display performance
		-p --profile                    profile gl display
		-k --toolkit [glut|qt5|pyglet]  choose toolkit (defaults to %(toolkit)r)
		-m --margin <size>              add a margin (defaults to %(margin)s)
		[doc.svg]                       file to show (if omitted, reads on stdin)
	""" % dict(name=name, **DEFAULTS))
	if message:
		sys.stderr.write("%s\n" % message)
	sys.stderr.write(usage)
	sys.exit(code)

try:
	options, args = getopt.getopt(args, "hcftpk:m:",
	                                    ["help",
	                                     "core", "fast", "time", "profile",
	                                     "toolkit=", "margin="])
except getopt.GetoptError as message:
	exit_usage(message, 1)

core    = DEFAULTS["core"]
fast    = DEFAULTS["fast"]
time    = DEFAULTS["time"]
profile = DEFAULTS["profile"]
toolkit = DEFAULTS["toolkit"]
margin  = DEFAULTS["margin"]

for opt, value in options:
	if opt in ["-h", "--help"]:
		exit_usage()
	elif opt in ["-c", "--core"]:
		core = True
	elif opt in ["-f", "--fast"]:
		fast = True
	elif opt in ["-t", "--time"]:
		time = True
	elif opt in ["-p", "--profile"]:
		profile = True
	elif opt in ["-k", "--toolkit"]:
		toolkit = value
		if toolkit not in ["glut", "qt5", "pyglet"]:
			exit_usage("toolkit should be one of [glut|qt5|pyglet]", 1)
	elif opt in ["-m", "--margin"]:
		margin = int(value)


if len(args) > 1:
	exit_usage("at most one file name should be provided", 1)

try:
	filename, = args
except:
	svg = sys.stdin.read()
else:
	import os
	old_cwd = os.getcwd()
	path, filename = os.path.split(filename)
	if path:
		os.chdir(path)
	if filename.endswith('z'):
		import gzip
		f = gzip.open(filename)
	else:
		f = open(filename)
	svg = f.read()
	f.close()
	os.chdir(old_cwd)


# scene ######################################################################

if fast:
	import OpenGL
	OpenGL.ERROR_CHECKING = False
	OpenGL.ERROR_LOGGING = False
	OpenGL.ERROR_ON_COPY = True
	OpenGL.STORE_POINTERS = False

from seagull import scenegraph as sg
from seagull.scenegraph.transform import product, normalized
from seagull.xml import parse, serialize
from seagull.opengl.utils import gl_prepare, gl_reshape, gl_display

svg, elems = parse(svg)

(x_min, y_min), (x_max, y_max) = svg.aabbox()
window_size = int(x_max-x_min+2*margin), int(y_max-y_min+2*margin)

scene = sg.Use(svg, transform=[sg.Translate(margin-x_min, margin-y_min)])
feedback = sg.Group(fill=None, stroke=sg.Color.red)


# display ####################################################################

def profiling(f):
	"""a profiling decorator"""
	import cProfile, pstats, atexit
	pr = cProfile.Profile()
	
	@atexit.register
	def report():
		ps = pstats.Stats(pr).sort_stats("tottime")
		ps.print_stats()
	
	def profiled(*args, **kwargs):
		pr.enable()
		try:
			f(*args, **kwargs)
		finally:
			pr.disable()
	return profiled

def timing(f):
	"""a timing decorator"""
	import time
	def timed(*args, **kwargs):
		start = time.time()
		try:
			f(*args, **kwargs)
		finally:
			stop = time.time()
			print(1./(stop-start))
	return timed


if profile:
	gl_display = profiling(gl_display)

if time:
	gl_display = timing(gl_display)


# screenshot #################################################################

_shot = 0
def screen_shot(name="screen_shot.%03i.png"):
	"""window screenshot."""
	from OpenGL.GL import glGetIntegerv, glReadPixels, GL_VIEWPORT, GL_RGB, GL_UNSIGNED_BYTE
	x, y, width, height = glGetIntegerv(GL_VIEWPORT)
	data = glReadPixels(x, y, width, height, GL_RGB, GL_UNSIGNED_BYTE)
	
	from demos.common import png
	global _shot
	png.write(open(name % _shot, "wb"), width, height, 3, data)
	_shot += 1


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


def keyboard(c):
	if c == 'q':
		sys.exit(0)
	elif c == 's':
		sys.stdout.write(serialize(scene))
	elif c == 'p':
		screen_shot()
	post_redisplay()


# main #######################################################################

"""toolkit dependent code"""

if toolkit == "glut":
	from OpenGL.GLUT import *
	
	glutInit(sys.argv)
	
	options = ["rgba", "double", "stencil", "samples", "hidpi"]
	if core:
		options += ["core"]
	glutInitDisplayString(" ".join(options).encode())
	glutInitWindowSize(*window_size)
	glutCreateWindow(name.encode())
	
	def display_func():
		gl_display(scene, feedback)
		glutSwapBuffers()
	
	BUTTONS = {
		GLUT_LEFT_BUTTON:   LEFT,
		GLUT_MIDDLE_BUTTON: MIDDLE,
		GLUT_RIGHT_BUTTON:  RIGHT,
	}
	
	def mouse_func(button, state, x, y):
		if state == GLUT_DOWN:
			try:
				press(BUTTONS[button], x, y)
			except KeyError:
				pass
		elif state == GLUT_UP:
			release()
	
	def keyboard_func(c, x, y):
		return keyboard(chr(c[0]))
	
	motion_func = move
	post_redisplay = glutPostRedisplay
	
	gl_prepare()
	glutReshapeFunc(gl_reshape)
	glutDisplayFunc(display_func)
	
	glutMouseFunc(mouse_func)
	glutMotionFunc(motion_func)
	glutPassiveMotionFunc(motion_func)
	glutKeyboardFunc(keyboard_func)
	
	glutMainLoop()


elif toolkit == "qt5":
	from PyQt5.QtCore import Qt, QEvent
	from PyQt5.QtGui import (QGuiApplication, QWindow, QSurfaceFormat,
	                         QOpenGLContext, QOpenGLPaintDevice)
	
	app = QGuiApplication(sys.argv)
	window = QWindow()
	
	format = QSurfaceFormat()
	format.setSwapBehavior(QSurfaceFormat.DoubleBuffer)
	format.setSamples(16)
	format.setStencilBufferSize(8)
	if core:
		format.setProfile(QSurfaceFormat.CoreProfile)
	
	window.setSurfaceType(QWindow.OpenGLSurface)
	window.setFormat(format)
	window.setTitle(name)
	
	pixel_ratio = window.devicePixelRatio()
	window.resize(*(u/pixel_ratio for u in window_size))
	
	gl_context = QOpenGLContext(window)
	gl_context.setFormat(window.requestedFormat())
	gl_context.create()
	
	
	# asynchronous redisplay
	
	def redisplay():
		gl_display(scene, feedback)
		gl_context.swapBuffers(window)
	
	waiting_redisplay = False
	def post_redisplay():
		global waiting_redisplay
		if not waiting_redisplay:
			waiting_redisplay = True
			app.postEvent(app, QEvent(QEvent.UpdateRequest))
	
	_event = app.event
	def event(event):
		global waiting_redisplay
		if event.type() == QEvent.UpdateRequest:
			waiting_redisplay = False
			redisplay()
			return True
		return _event(event)
	app.event = event
	
	
	# managing expose event
	
	device = None
	def expose_event(event):
		if not window.isExposed():
			return
		global device
		gl_context.makeCurrent(window)
		if not device:
			device = QOpenGLPaintDevice()
			gl_prepare()
		device.setSize(window.size())
		redisplay()
	window.exposeEvent = expose_event
	window.show()
	
	
	# managing interaction
	
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
		event.accept()
	
	def mouse_release(event):
		release()
		event.accept()
	
	def wheel(event):
		x, y = xy(event)
		press(MIDDLE, x, y)
		delta = event.angleDelta()
		move(x+delta.x(), y+delta.y())
		release()
		event.accept()
	
	def mouse_move(event):
		move(*xy(event))
		event.accept()
	
	def key_release(event):
		keyboard(event.text())
	
	window.mousePressEvent = mouse_press
	window.mouseReleaseEvent = mouse_release
	window.mouseMoveEvent = mouse_move
	window.wheelEvent = wheel
	window.keyReleaseEvent = key_release
	
	sys.exit(app.exec_())


elif toolkit == "pyglet":
	import pyglet
	
	print("warning: on cocoa, pyglet does not support retina display and core profile")
	
	config = pyglet.gl.Config(
		double_buffer=True,
		sample_buffers=1, samples=16,
		stencil_size=8,
	)
	if core:
		# does not seem to be implemented for pyglet/cocoa
		config.major_version = 3
		config.minor_version = 2
	
	width, height = window_size
	window = pyglet.window.Window(
		width=width, height=height,
		resizable=True, config=config,
	)
	
	gl_prepare()
	
	@window.event
	def on_resize(width, height):
		gl_reshape(width, height)
	
	@window.event
	def on_draw():
		gl_display(scene, feedback)
	
	@window.event
	def on_key_press(symbol, modifiers):
		keyboard(chr(symbol))

	BUTTONS = {
		pyglet.window.mouse.LEFT:   LEFT,
		pyglet.window.mouse.MIDDLE: MIDDLE,
		pyglet.window.mouse.RIGHT:  RIGHT,
	}
	
	@window.event
	def on_mouse_press(x, y, button, modifiers):
		press(BUTTONS[button], x, window.height-y)
	
	@window.event
	def on_mouse_release(x, y, button, modifiers):
		release()

	@window.event
	def on_mouse_motion(x, y, dx, dy):
		move(x, window.height-y)
	
	@window.event
	def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
		move(x, window.height-y)
	
	def post_redisplay():
		"""pyglet redisplays automatically after handled events."""
	
	pyglet.app.run()
