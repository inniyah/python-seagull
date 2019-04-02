#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import random
import pyglet
import fluidsynth
import midi
from threading import Thread

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

class RandomSoundPlayer():
    def __init__(self, keyboard_handler=None):
        self.keyboard_handler = keyboard_handler
        self.fs = fluidsynth.Synth()
        self.fs.start(driver="alsa")
        print("FluidSynth Started")
        self.sfid = self.fs.sfload("/usr/share/sounds/sf2/FluidR3_GM.sf2")
        self.fs.program_select(0, self.sfid, 0, 0)
    def __del__(self): # See:https://eli.thegreenplace.net/2009/06/12/safely-using-destructors-in-python/
        self.fs.delete()
        print("FluidSynth Closed")
        del self.fs
    def press(self, key, velocity=64, duration=0.5):
        self.fs.noteon(0, key + 19, velocity)
        if self.keyboard_handler: self.keyboard_handler.press(key + 19, True)
        time.sleep(duration)
        self.fs.noteoff(0, key + 19)
        if self.keyboard_handler: self.keyboard_handler.press(key + 19, False)
    @staticmethod
    def random_key(mean_key=44):
        x = random.gauss(mean_key, 10.0)
        if x < 1: x = 1
        elif x > 88: x = 88
        return int(round(x))
    @staticmethod
    def random_velocity():
        x = random.gauss(100.0, 10.0)
        if x < 1: x = 1
        elif x > 127: x = 127
        return int(round(x))
    @staticmethod
    def random_duration(self, mean_duration=2.0):
        x = random.gauss(mean_duration, 2.0)
        if x < 0.2: x = 0.2
        return x
    def random_play(self, num, mean_key, mean_duration):
        while num != 0:
            num -= 1
            key = self.random_key(mean_key)
            velocity = self.random_velocity()
            duration = self.random_duration(mean_duration)
            self.press(key, velocity, duration)
        #if self.keyboard_handler: self.keyboard_handler.show(False)

class MidiSoundPlayer():
    def __init__(self, filename, keyboard_handler=None):
        self.keyboard_handler = keyboard_handler
        self.fs = fluidsynth.Synth()
        self.fs.start(driver="alsa")
        print("FluidSynth Started")
        self.sfid = self.fs.sfload("/usr/share/sounds/sf2/FluidR3_GM.sf2")
        self.fs.program_select(0, self.sfid, 0, 0)
        self.midi = midi.MidiFile()
        self.midi.open(filename)
        self.midi.read()
        self.midi.close()
    def __del__(self): # See:https://eli.thegreenplace.net/2009/06/12/safely-using-destructors-in-python/
        self.fs.delete()
        print("FluidSynth Closed")
        del self.fs

def adj_color(red, green, blue, factor):
    return (int(red*factor), int(green*factor), int(blue*factor))

class MusicKeybOctave():
    NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    # See: https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/
    COLORS_RGB = [
        (230, 25, 75),   (60, 180, 75),   (255, 225, 25),  (67, 99, 216),   (245, 130, 49),
        (145, 30, 180),  (66, 212, 244),  (240, 50, 230),  (191, 239, 69),  (250, 190, 190),
        (70, 153, 144),  (230, 190, 255), (154, 99, 36),   (255, 250, 200), (128, 0, 0),
        (170, 255, 195), (128, 128, 0),   (255, 216, 177), (0, 0, 117),     (169, 169, 169),
    ]

    COLORS = [
        [sg.Color(*adj_color(r, g, b, 1.25)) for (r, g, b) in COLORS_RGB], # White keys
        [sg.Color(*adj_color(r, g, b, 1.0/1.25)) for (r, g, b) in COLORS_RGB], # Black keys
    ]

    def __init__(self):
        with open(os.path.join(this_dir, "PianoKeyboard.svg")) as f:
            svg = f.read()
        self.model_root, self.model_elements = parse(svg)
        #sys.stdout.write(serialize(self.model_root))
        #sys.stdout.write("elements = %s\n" % (self.model_elements,))
        json.dump(self.model_root, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
        #json.dump(self.model_elements, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
        #sys.stdout.write("\n") # Python JSON dump misses last newline
        self.orig_fill_color = {}
        for note in self.NOTES:
            self.orig_fill_color[note] = self.model_elements[note].fill
    def root(self):
        return self.model_root
    def size(self):
        (x_min, y_min), (x_max, y_max) = self.model_root.aabbox()
        return (x_max - x_min), (y_max - y_min)
    def press(self, key, action=True):
        if action:
            self.model_elements[key].fill = self.COLORS[0 if len(key) == 1 else 1][10]
        else:
            self.model_elements[key].fill = self.orig_fill_color[key]

class MusicKeyboard():
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
        piano.octaves[num_octave].press(MusicKeybOctave.NOTES[num_key % 12], action)
    def show(self, active=True):
        self.model_root.active = active

piano = MusicKeyboard()
scene = piano.root()
window_size = int(piano.width + 2 * margin), int(piano.height + 2 * margin)

feedback = sg.Group(fill=None, stroke=sg.Color.red)

midi_player = RandomSoundPlayer(piano)
midi_thread = Thread(target = midi_player.random_play, args = (8, 10, 0.3))
midi_thread.start()

midi_file_player = MidiSoundPlayer(os.path.join(this_dir, 'Bach_Fugue_BWV578.mid'), piano)

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

midi_thread.join()
print("All threads finished")
