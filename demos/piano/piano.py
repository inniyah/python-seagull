#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import pyglet

this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(this_dir, '..', '..'))

from seagull import scenegraph as sg
from seagull.xml import parse, serialize
from seagull.opengl.utils import gl_prepare, gl_reshape, gl_display
from seagull.scenegraph.transform import product, normalized

# This class escapes a string, by replacing control characters by their hexadecimal equivalents
class escape(str): # pylint: disable=invalid-name
    def __repr__(self):
        return ''.join('\\x{:02x}'.format(ord(ch)) if ord(ch) < 32 else ch for ch in self)
    __str__ = __repr__

class JSONDebugEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return sorted(obj)
        if isinstance(obj, sg.Element):
            return [
                ['%s' % (c,) for c in type.mro(type(obj))],
                obj.__dict__,
            ]
        if isinstance(obj, object):
            return [
                ['%s' % (c,) for c in type.mro(type(obj))],
                obj.__dict__,
            ]
        try:
            ret = json.JSONEncoder.default(self, obj)
        except:
            ret = ('%s' % (obj,))
        return ret

fast = True
margin = 20

if fast:
    import OpenGL
    OpenGL.ERROR_CHECKING = False
    OpenGL.ERROR_LOGGING = False
    OpenGL.ERROR_ON_COPY = True
    OpenGL.STORE_POINTERS = False

class MusicKeybOctave():
    def __init__(self):
        with open(os.path.join(this_dir, "PianoKeyboard.svg")) as f:
            svg = f.read()
        self.model_root, self.model_elements = parse(svg)
        #sys.stdout.write(serialize(self.model_root))
        #sys.stdout.write("elements = %s\n" % (self.model_elements,))
        json.dump(self.model_root, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
        #json.dump(self.model_elements, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
        #sys.stdout.write("\n") # Python JSON dump misses last newline
    def root(self):
        return self.model_root
    def size(self):
        (x_min, y_min), (x_max, y_max) = self.model_root.aabbox()
        return (x_max - x_min), (y_max - y_min)
    def press(self, key, action=True):
        self.model_elements[key].fill = sg.Color.red

class MusicKeyboard():
    NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    def __init__(self, num_octaves=10):
        self.octaves = [MusicKeybOctave() for i in range(0, num_octaves)]
        self.elements = []
        self.width = 0
        self.height = 0
        for octave in self.octaves:
            (x_min, y_min), (x_max, y_max) = octave.root().aabbox()
            element = sg.Use(
                octave.root(),
                transform=[sg.Translate(margin - x_min + self.width, margin - y_min)]
            )
            self.elements.append(element)
            self.width += x_max - x_min - 1
            self.height = y_max - y_min - 1
        self.model_root = sg.Group(self.elements)
    def root(self):
        return self.model_root
    def press(self, num_key, action=True):
        num_octave = num_key // 12
        piano.octaves[num_octave].press(self.NOTES[num_key % 12], action)

piano = MusicKeyboard()
scene = piano.root()
window_size = int(piano.width + 2 * margin), int(piano.height + 2 * margin)

feedback = sg.Group(fill=None, stroke=sg.Color.red)

#piano.press(3)

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
    pass

pyglet.clock.schedule_interval(update, 1/60, window)

pyglet.app.run()
