#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import random
import pyglet
import fluidsynth
import rtmidi
import mido
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
    def __init__(self, keyboard_handlers=None):
        self.keyboard_handlers = keyboard_handlers
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
        if self.keyboard_handlers:
            for keyboard_handler in self.keyboard_handlers:
                keyboard_handler.press(key + 19, 1, True)
        time.sleep(duration)
        self.fs.noteoff(0, key + 19)
        if self.keyboard_handlers:
            for keyboard_handler in self.keyboard_handlers:
                keyboard_handler.press(key + 19, 1, False)
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

class MidiFileSoundPlayer():
    def __init__(self, filename, keyboard_handlers=None):
        self.keyboard_handlers = keyboard_handlers
        self.fs = fluidsynth.Synth()
        self.fs.start(driver="alsa")
        print("FluidSynth Started")
        self.sfid = self.fs.sfload("/usr/share/sounds/sf2/FluidR3_GM.sf2")
        for channel in range(0, 16):
            self.fs.program_select(channel, self.sfid, 0, 0)
        self.midi_file = mido.MidiFile(filename)
        print('Midi File: {}'.format(self.midi_file.filename))
        length = self.midi_file.length
        print('Song length: {} minutes, {} seconds'.format(int(length / 60), int(length % 60)))
        print('Tracks:')
        for i, track in enumerate(self.midi_file.tracks):
            print('  {:2d}: {!r}'.format(i, track.name.strip()))

    def play(self):
        for message in self.midi_file.play(meta_messages=True):
            sys.stdout.write(repr(message) + '\n')
            sys.stdout.flush()
            if isinstance(message, mido.Message):
                if message.type == 'note_on':
                    self.fs.noteon(message.channel, message.note, message.velocity)
                    if self.keyboard_handlers:
                        for keyboard_handler in self.keyboard_handlers:
                            keyboard_handler.press(message.note, message.channel, True)

                elif message.type == 'note_off':
                    self.fs.noteoff(message.channel, message.note)
                    if self.keyboard_handlers:
                        for keyboard_handler in self.keyboard_handlers:
                            keyboard_handler.press(message.note, message.channel, False)

            elif message.type == 'set_tempo':
                print('Tempo changed to {:.1f} BPM.'.format(mido.tempo2bpm(message.tempo)))

    def __del__(self): # See:https://eli.thegreenplace.net/2009/06/12/safely-using-destructors-in-python/
        self.fs.delete()
        print("FluidSynth Closed")
        del self.fs

class RtMidiSoundPlayer():
    def __init__(self, keyboard_handlers=None):
        self.keyboard_handlers = keyboard_handlers
        self.fs = fluidsynth.Synth()
        self.fs.start(driver="alsa")
        print("FluidSynth Started")
        self.sfid = self.fs.sfload("/usr/share/sounds/sf2/FluidR3_GM.sf2")
        self.fs.program_select(0, self.sfid, 0, 0)

        self.midi_in = rtmidi.MidiIn()
        available_ports = self.midi_in.get_ports()
        if available_ports:
            midi_port_num = 1
            self.midi_in_port = self.midi_in.open_port(midi_port_num)
            print("Using MIDI Interface {}: '{}'".format(midi_port_num, available_ports[midi_port_num]))
        else:
            print("Creating virtual MIDI input.")
            self.midi_in_port = self.midi_in.open_virtual_port("midi_driving_in")

        self.midi_in.set_callback(self.midi_received)

    def __del__(self): # See:https://eli.thegreenplace.net/2009/06/12/safely-using-destructors-in-python/
        self.fs.delete()
        print("FluidSynth Closed")
        del self.fs

    def midi_received(self, midi_event, data=None):
        current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        midi_msg, delta_time = midi_event
        if len(midi_msg) > 2:
            pressed = (midi_msg[2] != 0)
            note = midi_msg[1]
            pitch_class = midi_msg[1] % 12
            octave = midi_msg[1] // 12

            print("%s" % ((pressed, note, octave, pitch_class),))

            if pressed: # A note was hit
                if self.keyboard_handlers:
                    for keyboard_handler in self.keyboard_handlers:
                        keyboard_handler.press(midi_msg[1], 1, True)

            else: # A note was released
                if self.keyboard_handlers:
                    for keyboard_handler in self.keyboard_handlers:
                        keyboard_handler.press(midi_msg[1], 1, False)





def adj_color(red, green, blue, factor=1.0):
    return (int(red*factor), int(green*factor), int(blue*factor))

# See: https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/
COLORS_RGB = [
    (60, 180, 75),   (230, 25, 75),   (67, 99, 216),   (255, 225, 25),  (245, 130, 49),
    (145, 30, 180),  (66, 212, 244),  (240, 50, 230),  (191, 239, 69),  (250, 190, 190),
    (70, 153, 144),  (230, 190, 255), (154, 99, 36),   (255, 250, 200), (128, 0, 0),
    (170, 255, 195), (128, 128, 0),   (255, 216, 177), (0, 0, 117),     (169, 169, 169),
]

class FifoList():
    def __init__(self):
        self.data = {}
        self.nextin = 0
        self.nextout = 0
    def append(self, data):
        self.nextin += 1
        self.data[self.nextin] = data
    def pop(self):
        self.nextout += 1
        result = self.data[self.nextout]
        del self.data[self.nextout]
        return result
    def peek(self):
        return self.data[self.nextout + 1] if self.data else None

class CircleOfFifths():
    NOTES = ['C', 'G', 'D', 'A', 'E', 'Cb', 'Gb', 'Db', 'Ab', 'Eb', 'Bb', 'F']
    COLORS = [sg.Color(*adj_color(r, g, b)) for (r, g, b) in COLORS_RGB]
    MEM_COLOR = sg.Color(169, 169, 169)
    MEM_COLORS = [ sg.Color(int(169.*i/10.) , int(169.*i/10.), int(169.*i/10.)) for i in range(0,10)]
    MEM_THRESHOLD = 10.0 # In floating-point seconds

    def __init__(self, x_pos=0, y_pos=0):
        with open(os.path.join(this_dir, "CircleOfFifths.svg")) as f:
            svg = f.read()
        self.model_root, self.model_elements = parse(svg)
        #sys.stdout.write(serialize(self.model_root))
        #sys.stdout.write("elements = %s\n" % (self.model_elements,))
        json.dump(self.model_root, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
        #json.dump(self.model_elements, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
        #sys.stdout.write("\n") # Python JSON dump misses last newline
        (x_min, y_min), (x_max, y_max) = self.model_root.aabbox()
        self.width = x_max - x_min
        self.height = y_max - y_min
        self.model_root = sg.Use(
            self.model_root,
            transform=[sg.Translate(margin - x_min + x_pos, margin - y_min + y_pos)]
        )

        self.press_counter = [0] * 12
        self.memory_counter = [0] * 12

        self.last_timestamp_present = self.last_timestamp_past = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        self.time_counter_present = [0] * 12
        self.total_time_counter_present = 0
        self.press_counter_past = [0] * 12

        self.last_notes = FifoList()

        self.orig_fill_color = {}
        for note in self.NOTES:
            label = 'inner_' + note
            self.orig_fill_color[label] = self.model_elements[label].fill
            label = 'outer_' + note
            self.orig_fill_color[label] = self.model_elements[label].fill

    def root(self):
        return self.model_root

    def size(self):
        (x_min, y_min), (x_max, y_max) = self.model_root.aabbox()
        return (x_max - x_min), (y_max - y_min)

    def adj_memory(self):
        for num_note in range(0, 12):
            note = self.NOTES[num_note]
            inner_label = 'inner_' + note
            if self.press_counter[num_note] > 0 or self.memory_counter[num_note] > 0:
                self.model_elements[inner_label].fill = self.MEM_COLOR
            else:
                self.model_elements[inner_label].fill = self.orig_fill_color[inner_label]

    def update(self):
        current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        delta_timestamp = current_timestamp - self.last_timestamp_past
        threshold_timestamp = current_timestamp - self.MEM_THRESHOLD

        data = self.last_notes.peek()
        while data is not None:
            timestamp, action, num_key, num_octave, num_note, note, channel = data
            inner_label = 'inner_' + note
            outer_label = 'outer_' + note

            data = None
            if timestamp < threshold_timestamp:
                self.last_notes.pop()
                #print("%s" % ((action, num_key, num_octave, num_note, note, channel),))

                if not action:
                    self.memory_counter[num_note] -= 1

                if self.press_counter[num_note] > 0 or self.memory_counter[num_note] > 0:
                    self.model_elements[inner_label].fill = self.MEM_COLOR
                else:
                    self.model_elements[inner_label].fill = self.orig_fill_color[inner_label]

        self.adj_memory()
        self.last_timestamp_past = current_timestamp

    def press(self, num_key, channel, action=True):
        current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        delta_timestamp = current_timestamp - self.last_timestamp_present

        self.total_time_counter_present += delta_timestamp
        for num_note in range(0, 12):
            if self.press_counter[num_note] > 0:
                self.time_counter_present[num_note] += delta_timestamp

        num_octave = num_key // 12
        num_note = (num_key*7)%12 % 12
        note = self.NOTES[num_note]
        inner_label = 'inner_' + note
        outer_label = 'outer_' + note

        self.last_notes.append((current_timestamp, action, num_key, num_octave, num_note, note, channel))

        if action:
            self.press_counter[num_note] += 1
            self.memory_counter[num_note] += 1
        else:
            self.press_counter[num_note] -= 1

        if self.press_counter[num_note] > 0:
            self.model_elements[outer_label].fill = self.COLORS[channel]
        else:
            self.model_elements[outer_label].fill = self.orig_fill_color[outer_label]

        self.adj_memory()
        self.last_timestamp_present = current_timestamp

class MusicKeybOctave():
    NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    COLORS = [
        [sg.Color(*adj_color(r, g, b, factor=1.25)) for (r, g, b) in COLORS_RGB], # White keys
        [sg.Color(*adj_color(r, g, b, factor=1.0/1.25)) for (r, g, b) in COLORS_RGB], # Black keys
    ]

    def __init__(self):
        with open(os.path.join(this_dir, "PianoKeyboard.svg")) as f:
            svg = f.read()
        self.model_root, self.model_elements = parse(svg)
        #sys.stdout.write(serialize(self.model_root))
        #sys.stdout.write("elements = %s\n" % (self.model_elements,))
        #json.dump(self.model_root, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
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
    def press(self, key, channel):
        self.model_elements[key].fill = self.COLORS[0 if len(key) == 1 else 1][channel]
    def release(self, key):
        self.model_elements[key].fill = self.orig_fill_color[key]

class MusicKeyboard():
    def __init__(self, num_octaves=10):
        self.octaves = [MusicKeybOctave() for i in range(0, num_octaves)]
        self.elements = []
        self.width = 0
        self.height = 0
        self.keys_pressed = [0] * (12 * num_octaves)
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
    def press(self, num_key, channel, action=True):
        num_octave = num_key // 12
        if action:
            self.keys_pressed[num_key] |= (1<<channel)
            if self.keys_pressed[num_key]:
                piano.octaves[num_octave].press(MusicKeybOctave.NOTES[num_key % 12], channel)
        else:
            self.keys_pressed[num_key] &= ~(1<<channel)
            if not self.keys_pressed[num_key]:
                piano.octaves[num_octave].release(MusicKeybOctave.NOTES[num_key % 12])
    def show(self, active=True):
        self.model_root.active = active

piano = MusicKeyboard()
fifths = CircleOfFifths(piano.width + margin)
scene = sg.Group([piano.root(), fifths.root()])

window_size = int(piano.width + margin + fifths.width + 2 * margin), int(piano.height + 2 * margin)

feedback = sg.Group(fill=None, stroke=sg.Color.red)

#midi_player = RandomSoundPlayer([piano, fifths])
#midi_thread = Thread(target = midi_player.random_play, args = (8, 10, 0.3))
#midi_thread.start()

midi_file_player = MidiFileSoundPlayer(os.path.join(this_dir, 'Bach_Fugue_BWV578.mid'), [piano, fifths])
midi_thread = Thread(target = midi_file_player.play)
midi_thread.start()

#midi_input = RtMidiSoundPlayer([piano, fifths])

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
    fifths.update()

pyglet.clock.schedule_interval(update, 1/60, window)

pyglet.app.run()

midi_thread.join()
print("All threads finished")
