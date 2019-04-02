#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(this_dir, '..', '..'))

from seagull import scenegraph as sg
from seagull.scenegraph.transform import product, normalized
from seagull.xml import parse, serialize
from seagull.opengl.utils import gl_prepare, gl_reshape, gl_display

fast = True
margin = 20

if fast:
    import OpenGL
    OpenGL.ERROR_CHECKING = False
    OpenGL.ERROR_LOGGING = False
    OpenGL.ERROR_ON_COPY = True
    OpenGL.STORE_POINTERS = False

with open(os.path.join(this_dir, "rgb_lights.svg")) as f:
    svg = f.read()
    svg, elements = parse(svg)
    #sys.stdout.write(serialize(svg))
    #sys.stdout.write("elements = %s\n" % (elements,))

(x_min, y_min), (x_max, y_max) = svg.aabbox()
window_size = int(x_max-x_min+2*margin), int(y_max-y_min+2*margin)

scene = sg.Use(svg, transform=[sg.Translate(margin-x_min, margin-y_min)])
feedback = sg.Group(fill=None, stroke=sg.Color.red)

elements['red'].active = False
elements['green'].active = True
elements['blue'].active = False

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

#gl_display = profiling(gl_display)

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

#gl_display = timing(gl_display)

import pyglet

width, height = window_size
window = pyglet.window.Window(
    width=width,
    height=height,
    resizable=True,
    )

gl_prepare()

@window.event
def on_resize(width, height):
    gl_reshape(width, height)

@window.event
def on_draw():
    gl_display(scene, feedback)

def keyboard(c):
    if c == 'q':
        sys.exit(0)
    elif c == 's':
        sys.stdout.write(serialize(scene))

LEFT, MIDDLE, RIGHT = range(3)

def mouse_button(button, pressed, x, y):
    pass

def mouse_move(x1, y1, drag):
    pass

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
    mouse_button(BUTTONS[button], True, x, window.height-y)

@window.event
def on_mouse_release(x, y, button, modifiers):
    mouse_button(BUTTONS[button], False, x, window.height-y)

@window.event
def on_mouse_motion(x, y, dx, dy):
    mouse_move(x, window.height-y, False)

@window.event
def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
    mouse_move(x, window.height-y, True)

def update(dt, window=None):
    elements['red'].active = not elements['green'].active
    elements['green'].active = not elements['blue'].active
    elements['blue'].active = not elements['red'].active

pyglet.clock.schedule_interval(update, 1/60, window)

pyglet.app.run()
