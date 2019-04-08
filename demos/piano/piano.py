#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import math
import json
import time
import random
import argparse
import pyglet
import fluidsynth
import rtmidi
import mido
from threading import Thread, Lock

this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(this_dir, '..', '..'))
parser = argparse.ArgumentParser(description='Piano Demo')
parser.add_argument('-m', '--midi', type=str, help='Midi file', required=False, default=None)
parser.add_argument('-v', '--verbose', action="store_true", help="verbose output" )
args = parser.parse_args()

GRAD_COLORS = 30

if args.verbose:
	print("~ Verbose!")
else:
	print("~ Not so verbose")

print("~ Midi Filename: {}".format(args.midi))

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
        time.sleep(1)
        for message in self.midi_file.play(meta_messages=True):
            #sys.stdout.write(repr(message) + '\n')
            #sys.stdout.flush()
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
                #print('Tempo changed to {:.1f} BPM.'.format(mido.tempo2bpm(message.tempo)))
                pass

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
            try:
                self.midi_in_port = self.midi_in.open_port(midi_port_num)
            except rtmidi.InvalidPortError:
                print("Failed to open MIDI input")
                self.midi_in_port = None
                return
            print("Using MIDI input Interface {}: '{}'".format(midi_port_num, available_ports[midi_port_num]))
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

            #print("%s" % ((pressed, note, octave, pitch_class),))

            if pressed: # A note was hit
                if self.keyboard_handlers:
                    for keyboard_handler in self.keyboard_handlers:
                        keyboard_handler.press(midi_msg[1], 16, True)

            else: # A note was released
                if self.keyboard_handlers:
                    for keyboard_handler in self.keyboard_handlers:
                        keyboard_handler.press(midi_msg[1], 16, False)





def adj_color(red, green, blue, factor=1.0):
    return (int(red*factor), int(green*factor), int(blue*factor))

# See: https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/
COLORS_RGB = [
    (60, 180, 75),   (230, 25, 75),   (67, 99, 216),   (255, 225, 25),  (245, 130, 49),
    (145, 30, 180),  (66, 212, 244),  (240, 50, 230),  (191, 239, 69),  (250, 190, 190),
    (70, 153, 144),  (230, 190, 255), (154, 99, 36),   (255, 250, 200), (128, 0, 0),
    (170, 255, 195), (128, 128, 0),   (255, 216, 177), (0, 0, 117),     (169, 169, 169),
]

COLORS = [sg.Color(*adj_color(r, g, b)) for (r, g, b) in COLORS_RGB]

class FifoList():
    def __init__(self):
        self.data = {}
        self.nextin = 0
        self.nextout = 0
        self.lock = Lock()
    def append(self, data):
        try:
            self.lock.acquire()
            self.nextin += 1
            self.data[self.nextin] = data
        finally:
            self.lock.release()
    def pop(self):
        try:
            self.lock.acquire()
            self.nextout += 1
            result = self.data[self.nextout]
            del self.data[self.nextout]
        finally:
            self.lock.release()
        return result
    def peek(self):
        try:
            self.lock.acquire()
            result = self.data[self.nextout + 1] if self.data else None
        finally:
            self.lock.release()
        return result


class FifthsWithMemory():
    NOTES = ['C', 'G', 'D', 'A', 'E', 'B', 'Gb', 'Db', 'Ab', 'Eb', 'Bb', 'F']

    # Forgetting factor: f(t) = 1.0 / (K ** ( t / T ))
    # Integral of f(t): F(t) = C - T / (logn(K) * K ** ( t / T ))
    # If F(t) == 0: C = T0 / logn(K)
    def mem_f(self, t): # when t -> inf, mem_f -> 0
        return 1.0 / (self.mem_k ** (t / self.mem_t))
    def mem_F(self, t): # when t -> inf, mem_F -> MEM_C
        return self.mem_c - self.mem_t / (math.log(self.mem_k) * (self.mem_k ** (t / self.mem_t)))

    def __init__(self, mem_t=1.0, mem_k=3.0, mem_threshold = 5.0):
        self.mem_t = mem_t # In T floating-point seconds
        self.mem_k = mem_k # The value will be divided by K. It needs to be > 1
        self.mem_c = self.mem_t / math.log(self.mem_k) # As calculated above

        self.press_counter = [0] * 12
        self.memory_counter = [0] * 12
        self.press_counter_past = [0] * 12
        self.accum_time = [0.] * 12

        self.mem_threshold = mem_threshold # In floating-point seconds
        self.last_notes = FifoList()

        self.last_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds

    def adjust_accum_time(self,  current_timestamp = None):
        if current_timestamp is None:
            current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        delta_timestamp = current_timestamp - self.last_timestamp

        for num_note in range(0, 12):
            self.accum_time[num_note] = self.accum_time[num_note] * self.mem_f(delta_timestamp) # Move current value into the past
            # Update accumulated time with previous value of press_counter, before updating it
            if self.press_counter[num_note] > 0:
                 self.accum_time[num_note] += self.mem_F(delta_timestamp) # Add more, if key pressed
        self.last_timestamp = current_timestamp
        #print("%s" % (self.accum_time,))

    def update(self, current_timestamp = None):
        if current_timestamp is None:
            current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        threshold_timestamp = current_timestamp - self.mem_threshold

        try:
            queue_timestamp = self.last_notes.peek()[0]
        except (TypeError, IndexError):
            queue_timestamp = None

        while not queue_timestamp is None and queue_timestamp < threshold_timestamp:
            timestamp, action, num_key, num_octave, num_note, note_id, channel = self.last_notes.pop()

            #print("%s" % ((action, num_key, num_octave, num_note, note, channel),))

            if action:
                self.press_counter_past[num_note] += 1
            else:
                self.press_counter_past[num_note] -= 1
                self.memory_counter[num_note] -= 1

            try:
                queue_timestamp = self.last_notes.peek()[0]
            except (TypeError, IndexError):
                queue_timestamp = None

        self.adjust_accum_time(current_timestamp)

    def press(self, num_key, channel, action, current_timestamp):
        if current_timestamp is None:
            current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds

        num_octave = num_key // 12
        num_note = (num_key*7)%12 % 12
        note_id = self.NOTES[num_note]

        self.last_notes.append((current_timestamp, action, num_key, num_octave, num_note, note_id, channel))

        if action:
            self.press_counter[num_note] += 1
            self.memory_counter[num_note] += 1
        else:
            self.press_counter[num_note] -= 1
            assert(self.press_counter[num_note] >= 0)

        self.adjust_accum_time(current_timestamp)

        return num_key, num_octave, num_note, note_id

class CircleOfFifths(FifthsWithMemory):
    MEM_COLORS = [ sg.Color(int(210.*(GRAD_COLORS-i)/GRAD_COLORS) , int(230.*(GRAD_COLORS-i)/GRAD_COLORS), int(250.*(GRAD_COLORS-i)/GRAD_COLORS)) for i in range(0, GRAD_COLORS+1)]
    MEM_THRESHOLD = 3.0 # In floating-point seconds

    # Forgetting factor: f(t) = 1.0 / (K ** ( t / T ))
    # Integral of f(t): F(t) = C - T / (logn(K) * K ** ( t / T ))
    # If F(t) == 0: C = T0 / logn(K)
    MEM_T = 1.0 # In T floating-point seconds
    MEM_K = 3.0 # The value will be divided by K. It needs to be > 1
    MEM_C = MEM_T / math.log(MEM_K) # As calculated above

    def __init__(self, x_pos=0, y_pos=0):
        super().__init__(self.MEM_T, self.MEM_K, self.MEM_THRESHOLD)

        with open(os.path.join(this_dir, "CircleOfFifths.svg")) as f:
            svg = f.read()
        self.model_root, self.model_elements = parse(svg)
        #sys.stdout.write(serialize(self.model_root))
        #sys.stdout.write("elements = %s\n" % (self.model_elements,))
        #json.dump(self.model_root, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
        #json.dump(self.model_elements, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
        #sys.stdout.write("\n") # Python JSON dump misses last newline
        (x_min, y_min), (x_max, y_max) = self.model_root.aabbox()
        self.width = x_max - x_min
        self.height = y_max - y_min
        self.model_root = sg.Use(
            self.model_root,
            transform=[sg.Translate(margin - x_min + x_pos, margin - y_min + y_pos)]
        )

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
                i = int(len(self.MEM_COLORS) * self.accum_time[num_note] / self.MEM_C)
                self.model_elements[inner_label].fill = self.MEM_COLORS[max(0, min(i, len(self.MEM_COLORS)-1))]
            else:
                self.model_elements[inner_label].fill = self.orig_fill_color[inner_label]

    def update(self):
        current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        super().update(current_timestamp)
        self.adj_memory()

    def press(self, num_key, channel, action=True):
        current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        num_key, num_octave, num_note, note_id = super().press(num_key, channel, action, current_timestamp)

        inner_label = 'inner_' + note_id
        outer_label = 'outer_' + note_id

        if self.press_counter[num_note] > 0:
            self.model_elements[outer_label].fill = COLORS[channel]
        else:
            self.model_elements[outer_label].fill = self.orig_fill_color[outer_label]

        self.adj_memory()


NOTES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'] * 2

class HexLayout():
    COLORS = [sg.Color(*adj_color(r, g, b)) for (r, g, b) in COLORS_RGB]
    MEM_COLORS = [
        sg.Color(
            int(180. - 120. * ((GRAD_COLORS-i)/GRAD_COLORS)**1.5),
            int(200. - 120. * ((GRAD_COLORS-i)/GRAD_COLORS)**1.5),
            int(210. - 120. * ((GRAD_COLORS-i)/GRAD_COLORS)**1.5)
        ) for i in range(0, GRAD_COLORS+1)]

    IDLE_COLOR = sg.Color(50, 50, 50)
    IDLE_STROKE = sg.Color(0, 0, 0)

    # Forgetting factor: f(t) = 1.0 / (K ** ( t / T ))
    # Integral of f(t): F(t) = C - T / (logn(K) * K ** ( t / T ))
    # If F(t) == 0: C = T0 / logn(K)
    MEM_T = 0.8 # In T floating-point seconds
    MEM_K = 2.0 # The value will be divided by K. It needs to be > 1
    MEM_C = MEM_T / math.log(MEM_K) # As calculated above

    def mem_f(self, t): # when t -> inf, mem_f -> 0
        return 1.0 / (self.MEM_K ** (t / self.MEM_T))

    def mem_F(self, t): # when t -> inf, mem_F -> MEM_C
        return self.MEM_C - self.MEM_T / (math.log(self.MEM_K) * (self.MEM_K ** (t / self.MEM_T)))

    def __init__(self, x_pos=0, y_pos=0):
        with open(os.path.join(this_dir, "HexLayout.svg")) as f:
            svg = f.read()
        self.model_root, self.model_elements = parse(svg)
        (x_min, y_min), (x_max, y_max) = self.model_root.aabbox()
        self.width = x_max - x_min
        self.height = y_max - y_min
        self.model_root = sg.Use(
            self.model_root,
            transform=[sg.Translate(margin - x_min + x_pos, margin - y_min + y_pos)]
        )

        self.press_counter = [0] * 12
        self.accum_time = [0.] * 12
        self.last_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds

        #self.note_map  = ['cC',  'cG',  'dD',  'dA',  'dE',  'dB', 'aGb', 'bDb', 'bAb', 'bEb', 'bBb', 'cF' ]
        #self.note_map  = ['cGb', 'cDb', 'dAb', 'dEb', 'dBb', 'dF', 'aC',  'bG',  'bD',  'bA',  'bE',  'cB' ]

        #self.note_map   = ['cEb', 'cBb', 'cF',  'dC',  'dG',  'dD', 'dA',  'bE_',  'bB',  'bGb', 'cDb_', 'cAb_']
        #self.note_map   = ['cEb', 'cBb', 'dF_',  'dC',  'dG',  'dD', 'aA',  'bE_',  'bB',  'bGb', 'bDb', 'cAb_']

        #self.note_map  = ['cGb', 'cDb', ['cAb', 'dAb'], 'dEb', ['aBb', 'dBb'], ['aF', 'dF', 'eF'] , ['aC', 'eC'],
        #                 ['aG', 'bG', 'eG'], ['bD', 'eD'],  'bA', ['bE', 'cE'], ['bB_', 'cB'] ]

        #self.note_map  = ['cC',  'cG',  'dD',  'dA',  'dE',  'dB',  'aGb', 'bDb', 'bAb', 'bEb', 'bBb', 'cF' ]
        #self.note_map  = ['cG',  'cD',  'dA',  'dE',  'dB',  'dGb', 'aDb', 'bAb', 'bEb', 'bBb', 'bF',  'cC' ]

        self.note_map  = [\
            [row + 'G'  for row in ['a', 'b', 'c', 'd', 'e']],
            [row + 'D'  for row in ['a', 'b', 'c', 'd', 'e']],
            [row + 'A'  for row in ['a', 'b', 'c', 'd', 'e']],
            [row + 'E'  for row in ['a', 'b', 'c', 'd', 'e']],
            [row + 'B'  for row in ['a', 'b', 'c', 'd', 'e']],
            [row + 'Gb' for row in ['a', 'b', 'c', 'd', 'e']],
            [row + 'Db' for row in ['a', 'b', 'c', 'd', 'e']],
            [row + 'Ab' for row in ['a', 'b', 'c', 'd', 'e']],
            [row + 'Eb' for row in ['a', 'b', 'c', 'd', 'e']],
            [row + 'Bb' for row in ['a', 'b', 'c', 'd', 'e']],
            [row + 'F'  for row in ['a', 'b', 'c', 'd', 'e']],
            [row + 'C'  for row in ['a', 'b', 'c', 'd', 'e']],
        ]
        for note_ids in self.note_map:
            if not isinstance(note_ids, (list, tuple)):
                note_ids = [note_ids]
            new_note_ids = [] 
            for note_id in note_ids:
                new_note_id = note_id + '_'
                if new_note_id in self.model_elements:
                    new_note_ids.append(new_note_id)
            note_ids += new_note_ids

        for note_ids in self.note_map:
            if not isinstance(note_ids, (list, tuple)):
                note_ids = [note_ids]
            for note_id in note_ids:
                self.model_elements[note_id].fill = self.IDLE_COLOR
                self.model_elements[note_id].stroke = self.IDLE_STROKE
                self.model_elements[note_id].stroke_width = 1

    def root(self):
        return self.model_root

    def size(self):
        (x_min, y_min), (x_max, y_max) = self.model_root.aabbox()
        return (x_max - x_min), (y_max - y_min)

    def update(self):
        current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        delta_timestamp = current_timestamp - self.last_timestamp

        for num_note in range(0, 12):
            self.accum_time[num_note] = self.accum_time[num_note] * self.mem_f(delta_timestamp) # Move current value into the past
            # Update accumulated time with previous value of press_counter, before updating it
            if self.press_counter[num_note] > 0:
                 self.accum_time[num_note] += self.mem_F(delta_timestamp) # Add more, if key pressed
        self.last_timestamp = current_timestamp
        #print("%s" % (self.accum_time,))

        for num_note in range(0, 12):
            note_ids = self.note_map[num_note]
            if not isinstance(note_ids, (list, tuple)):
                note_ids = [note_ids]
            if self.press_counter[num_note] > 0: # Note currently being pressed
                i = int(len(self.MEM_COLORS) * self.accum_time[num_note] / self.MEM_C)
                for note_id in note_ids:
                    self.model_elements[note_id].fill = self.MEM_COLORS[max(0, min(i, len(self.MEM_COLORS)-1))]
                pass
            elif self.accum_time[num_note] > 0.1 * self.MEM_C: # Note played recently, fresh in memory
                i = int(len(self.MEM_COLORS) * self.accum_time[num_note] / self.MEM_C)
                for note_id in note_ids:
                    self.model_elements[note_id].fill = self.MEM_COLORS[max(0, min(i, len(self.MEM_COLORS)-1))]
            else:
                for note_id in note_ids: # Note not used recently
                    self.model_elements[note_id].fill = self.IDLE_COLOR

    def press(self, num_key, channel, action=True):
        num_octave = num_key // 12
        num_note = (num_key*7)%12 % 12

        note_ids = self.note_map[num_note]
        if not isinstance(note_ids, (list, tuple)):
            note_ids = [note_ids]

        if action:
            self.press_counter[num_note] += 1
        else:
            self.press_counter[num_note] -= 1
        assert(self.press_counter[num_note] >= 0)

        for note_id in note_ids:
            if self.press_counter[num_note] > 0:
                self.model_elements[note_id].stroke = COLORS[channel]
                self.model_elements[note_id].stroke_width = 3
            else:
                self.model_elements[note_id].stroke = self.IDLE_STROKE
                self.model_elements[note_id].stroke_width = 1

        self.update()

class Chords(FifthsWithMemory):
    FIFTHS_NOTES    = ['C', 'G', 'D', 'A', 'E', 'B', 'Gb', 'Db', 'Ab', 'Eb', 'Bb', 'F']
    CHROMATIC_NOTES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

    MEM_COLORS_BLACK = [ sg.Color(
        int(128.*(i)/GRAD_COLORS),
        int(128.*(i)/GRAD_COLORS),
        int(128.*(i)/GRAD_COLORS)
    ) for i in range(0, GRAD_COLORS+1)]

    MEM_COLORS_WHITE = [ sg.Color(
        int(128.*(GRAD_COLORS-i)/GRAD_COLORS/2. + 128.),
        int(128.*(GRAD_COLORS-i)/GRAD_COLORS/2. + 128.),
        int(128.*(GRAD_COLORS-i)/GRAD_COLORS/2. + 128.)
    ) for i in range(0, GRAD_COLORS+1)]

    MEM_THRESHOLD = 5.0 # In floating-point seconds

    COLOR_BLACK = sg.Color(0, 0, 0)
    COLOR_GRAY = sg.Color(128, 128, 128)
    COLOR_WHITE = sg.Color(255, 255, 255)

    COLOR_WHITE_KEY_PRESSED = sg.Color(255, 211, 0)
    COLOR_BLACK_KEY_PRESSED = sg.Color(208, 168, 0)

    # Forgetting factor: f(t) = 1.0 / (K ** ( t / T ))
    # Integral of f(t): F(t) = C - T / (logn(K) * K ** ( t / T ))
    # If F(t) == 0: C = T0 / logn(K)
    MEM_T = 2.0 # In T floating-point seconds
    MEM_K = 2.0 # The value will be divided by K. It needs to be > 1
    MEM_C = MEM_T / math.log(MEM_K) # As calculated above

    CHORDS_INFO = [
        [ [], (0, 4, 7, 11, 14, 17, 21), sg.Color(0, 180, 100), "Major 13th Chord" ],
        [ [], (0, 4, 7, 10, 14, 17, 21), sg.Color(0, 180, 100), "Dominant 13th Chord" ],
        [ [], (0,    7, 11, 14, 17, 21), sg.Color(0, 180, 100), "Major 13th Chord, leaving out the 3rd" ],
        [ [], (0,    7, 10, 14, 17, 21), sg.Color(0, 180, 100), "Dominant 13th Chord, leaving out the 3rd" ],
        [ [], (0, 3, 7, 10, 14, 17, 21), sg.Color(0, 180, 100), "Minor 13th Chord" ],

        [ [], (0, 4, 7, 11, 14, 17), sg.Color(0, 180, 100), "Major 11th Chord" ],
        [ [], (0, 4, 7, 10, 14, 17), sg.Color(0, 180, 100), "Dominant 11th Chord" ],
        [ [], (0,    7, 11, 14, 17), sg.Color(0, 180, 100), "Major 11th Chord, leaving out the 3rd (maj9sus4)" ],
        [ [], (0,    7, 10, 14, 17), sg.Color(0, 180, 100), "Dominant 11th Chord, leaving out the 3rd (9sus4)" ],
        [ [], (0, 3, 7, 10, 14, 17), sg.Color(0, 180, 100), "Minor 11th Chord" ],

        [ [], (0, 4, 7, 11, 14), sg.Color(0, 180, 100), "Major 9th Chord" ],
        [ [], (0, 4, 7, 10, 14), sg.Color(0, 180, 100), "Dominant 9th Chord" ],
        [ [], (0, 3, 7, 10, 14), sg.Color(0, 180, 100), "Minor 9th Chord" ],

        [ [], (0, 4, 7, 10, 15), sg.Color(0, 100, 180), "7#9 Chord or 'Hendrix Chord'" ],
        [ [], (0, 4, 7, 10, 13), sg.Color(200, 0, 100), "'Irritating' 7b9 Chord" ],

        [ [], (0, 4,    11, 14, 17), sg.Color(0, 180, 100), "Major 11th Chord, leaving out the 5th" ],
        [ [], (0, 4,    10, 14, 17), sg.Color(0, 180, 100), "Dominant 11th Chord, leaving out the 5th" ],
        [ [], (0, 3,    10, 14, 17), sg.Color(0, 180, 100), "Minor 11th Chord, leaving out the 5th" ],

        [ [], (0, 4, 7, 11), sg.Color(0, 180, 100), "Major 7th Chord" ],
        [ [], (0, 4, 7, 10), sg.Color(0, 180, 100), "Dominant 7th Chord" ],
        [ [], (0, 3, 7, 10), sg.Color(100, 0, 200), "Minor 7th Chord" ],
        [ [], (0, 3, 6, 10), sg.Color(200, 0, 100), "Half-Diminished Minor 7th Chord" ],
        [ [], (0, 3, 6, 9),  sg.Color(200, 0, 100), "Diminished Minor 7th Chord" ],

        [ [], (0, 4, 7, 14), sg.Color(0, 180, 100), "Add9 Chord" ],
        [ [], (0, 4, 7, 9), sg.Color(0, 180, 100), "Add6 Chord" ],
        [ [], (0, 4, 5, 7), sg.Color(0, 180, 100), "Add4 Chord" ],
        [ [], (0, 2, 4, 7), sg.Color(0, 180, 100), "Add4 Chord" ],

        [ [], (0,       11, 14, 17), sg.Color(0, 180, 100), "Major 11th Chord, leaving out the 3rd and the 5th" ],
        [ [], (0,       10, 14, 17), sg.Color(0, 180, 100), "Dominant 11th Chord, leaving out the 3rd and the 5th" ],

        [ [], (0, 4, 7,  11, 21), sg.Color(0, 180, 100), "Major 13th Chord" ],
        [ [], (0, 4, 7,  10, 21), sg.Color(0, 180, 100), "Dominant 13th Chord" ],
        [ [], (0, 3, 7,  10, 21), sg.Color(0, 180, 100), "Minor 13th Chord" ],

        [ [], (0, 4,     11, 21), sg.Color(0, 180, 100), "Major 13th Chord, leaving out the 5th" ],
        [ [], (0, 4,     10, 21), sg.Color(0, 180, 100), "Dominant 13th Chord, leaving out the 5th" ],
        [ [], (0, 3,     10, 21), sg.Color(0, 180, 100), "Minor 13th Chord, leaving out the 5th" ],

        [ [], (0, 4,    11, 14), sg.Color(0, 180, 100), "Major 9th Chord, leaving out the 5th" ],
        [ [], (0, 4,    10, 14), sg.Color(0, 180, 100), "Dominant 9th Chord, leaving out the 5th" ],
        [ [], (0, 3,    10, 14), sg.Color(0, 180, 100), "Minor 9th Chord, leaving out the 5th" ],

        [ [], (0, 4, 7),  sg.Color(0, 180, 100), "Major Triad" ],
        [ [], (0, 3, 7),  sg.Color(100, 0, 200), "Minor Triad" ],
        [ [], (0, 3, 6),  sg.Color(200, 0, 100), "Diminished Triad" ],
        [ [], (0, 4, 8),  sg.Color(0, 100, 180), "Augmented Triad" ],
        [ [], (0, 2, 7),  sg.Color(180, 100, 0), "Sus2 Triad" ],
        [ [], (0, 7, 9),  sg.Color(180, 100, 0), "6Sus Triad" ],
        [ [], (0, 7, 10), sg.Color(180, 100, 0), "7Sus Triad" ],

        [ [], (0, 7), sg.Color(0, 180, 100), "Parallel Fifths" ],
        [ [], (0, 4), None, "Major Third Interval" ],
        [ [], (0, 3), None, "Minor Third Interval" ],
        [ [], (0, 11), None, "Major Seventh Interval" ],
    ]

    def __init__(self, x_pos=0, y_pos=0):
        super().__init__(self.MEM_T, self.MEM_K, self.MEM_THRESHOLD)

        for chord_info in self.CHORDS_INFO:
            if not chord_info[0]:
                chord_info[0] = [0] * 12
                for i in range(0, 12):
                    chord_mask = 0
                    for num_note in chord_info[1]:
                        chord_mask |= 1 << (i + num_note) % 12
                    chord_info[0][i] = chord_mask
            if chord_info[2] is None:
                chord_info[2] = self.COLOR_GRAY
        #json.dump(self.CHORDS_INFO, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)

        with open(os.path.join(this_dir, "ChordMatrix.svg")) as f:
            svg = f.read()
        self.model_root, self.model_elements = parse(svg)
        #sys.stdout.write(serialize(self.model_root))
        #sys.stdout.write("elements = %s\n" % (self.model_elements,))
        #json.dump(self.model_root, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
        #json.dump(self.model_elements, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
        #sys.stdout.write("\n") # Python JSON dump misses last newline
        (x_min, y_min), (x_max, y_max) = self.model_root.aabbox()
        self.width = x_max - x_min
        self.height = y_max - y_min
        self.model_root = sg.Use(
            self.model_root,
            transform=[sg.Translate(margin - x_min + x_pos, margin - y_min + y_pos)]
        )

        self.orig_fill_color = {}
        for note_id in self.CHROMATIC_NOTES:
            key_label = '{}'.format(note_id)
            self.orig_fill_color[key_label] = self.model_elements[key_label].fill
        for row in range(1,12):
            row_label = 'row{:02d}'.format(row)
            self.model_elements[row_label].active = False
            for note_id in self.CHROMATIC_NOTES:
                label = '{}{:02d}'.format(note_id, row)
                self.model_elements[label].active = False

    def root(self):
        return self.model_root

    def size(self):
        (x_min, y_min), (x_max, y_max) = self.model_root.aabbox()
        return (x_max - x_min), (y_max - y_min)

    def update_triads(self):
        for row in range(1, 12):
            row_label = 'row{:02d}'.format(row)
            self.model_elements[row_label].active = False
            for note_id in self.CHROMATIC_NOTES:
                label = '{}{:02d}'.format(note_id, row)
                self.model_elements[label].active = False

        for num_note in range(0, 12):
            note_id = self.FIFTHS_NOTES[num_note]
            key_label = '{}'.format(note_id)
            is_white = (len(key_label) == 1)

            if self.press_counter[num_note] > 0:
                self.model_elements[key_label].fill = self.COLOR_WHITE_KEY_PRESSED if is_white else self.COLOR_BLACK_KEY_PRESSED 
            elif self.memory_counter[num_note] > 0:
                colors = self.MEM_COLORS_WHITE if is_white else self.MEM_COLORS_BLACK
                i = int(len(colors) * self.accum_time[num_note] / self.MEM_C)
                self.model_elements[key_label].fill = colors[max(0, min(i, len(colors)-1))]
            else:
                self.model_elements[key_label].fill = self.orig_fill_color[key_label]

        row = 1
        max_row = 11

        pitch_classes = 0
        mem_pitch_classes = 0
        used_pitch_classes = 0
        for num_note in range(0, 12):
            value = 1 << ((num_note*7) % 12)
            if self.press_counter[num_note] > 0:
                pitch_classes |= value
            if self.memory_counter[num_note] > 0:
                mem_pitch_classes |= value

        for chord_signatures, chord_intervals, color, chord_name in self.CHORDS_INFO:
            for num_signature, chord_signature in enumerate(chord_signatures):
                if (pitch_classes & chord_signature) == chord_signature and (used_pitch_classes & chord_signature) != chord_signature:
                    row_label = 'row{:02d}'.format(row)
                    self.model_elements[row_label].active = True
                    self.model_elements[row_label].stroke = color
                    for interval in chord_intervals:
                        note_id = self.CHROMATIC_NOTES[(num_signature + interval) % 12]
                        label = '{}{:02d}'.format(note_id, row)
                        self.model_elements[label].fill = color
                        self.model_elements[label].active = True
                        self.model_elements[label].stroke = self.COLOR_BLACK
                        self.model_elements[label].stroke_width = 3 if interval == 0 else 1
                    used_pitch_classes |= chord_signature
                    print("Chord: {} on {})".format(chord_name, self.CHROMATIC_NOTES[(num_signature) % 12]))
                    row += 1
                else:
                    pass

    def update(self):
        current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        super().update(current_timestamp)
        self.update_triads()

    def press(self, num_key, channel, action=True):
        current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        num_key, num_octave, num_note, note_id = super().press(num_key, channel, action, current_timestamp)
        self.update_triads()

class CircleOfTriads(FifthsWithMemory):
    CIRCLES = ['z', 'y', 'x', 'w', 'v', 'u']

    # Forgetting factor: f(t) = 1.0 / (K ** ( t / T ))
    # Integral of f(t): F(t) = C - T / (logn(K) * K ** ( t / T ))
    # If F(t) == 0: C = T0 / logn(K)
    MEM_T = 2.0 # In T floating-point seconds
    MEM_K = 2.0 # The value will be divided by K. It needs to be > 1
    MEM_C = MEM_T / math.log(MEM_K) # As calculated above

    COLOR_BLACK = sg.Color(0, 0, 0)
    COLOR_GRAY = sg.Color(128, 128, 128)
    COLOR_WHITE = sg.Color(255, 255, 255)

    MEM_THRESHOLD = 0.5 # In floating-point seconds

    TRIADS_MAJOR      = [ (1<<i | 1<<((i+4)%12) | 1<<((i+7)%12)) for i in range(0, 12) ]
    TRIADS_MINOR      = [ (1<<i | 1<<((i+3)%12) | 1<<((i+7)%12)) for i in range(0, 12) ]
    TRIADS_DIMINISHED = [ (1<<i | 1<<((i+3)%12) | 1<<((i+6)%12)) for i in range(0, 12) ]
    TRIADS_AUGMENTED  = [ (1<<i | 1<<((i+4)%12) | 1<<((i+8)%12)) for i in range(0, 12) ]
    TRIADS_SUSPENDED  = [ (1<<i | 1<<((i+2)%12) | 1<<((i+7)%12)) for i in range(0, 12) ]
    PARALLEL_FIFTHS   = [ (1<<i | 1<<((i+7)%12)) for i in range(0, 12) ]

    def __init__(self, x_pos=0, y_pos=0):
        super().__init__(self.MEM_T, self.MEM_K, self.MEM_THRESHOLD)

        with open(os.path.join(this_dir, "CircleOfTriads.svg")) as f:
            svg = f.read()
        self.model_root, self.model_elements = parse(svg)
        (x_min, y_min), (x_max, y_max) = self.model_root.aabbox()
        self.width = x_max - x_min
        self.height = y_max - y_min
        self.model_root = sg.Use(
            self.model_root,
            transform=[sg.Translate(margin - x_min + x_pos, margin - y_min + y_pos)]
        )

        for note in self.NOTES:
            self.model_elements[note].stroke = self.COLOR_GRAY
            self.model_elements[note].stroke_width = 1
            self.model_elements[note].active = False
            for circle in self.CIRCLES:
                element_id = '{}{}'.format(circle, note)
                self.model_elements[element_id].fill = self.COLOR_WHITE
                self.model_elements[element_id].stroke = self.COLOR_GRAY
                self.model_elements[element_id].active = False

    def root(self):
        return self.model_root

    def size(self):
        (x_min, y_min), (x_max, y_max) = self.model_root.aabbox()
        return (x_max - x_min), (y_max - y_min)

    def update_triads(self):
        for triad_signatures, label_prefix, color_on, color_off in [
            (self.TRIADS_AUGMENTED,  'z', sg.Color(0, 100, 180),   sg.Color(215, 215, 255)),
            (self.TRIADS_MAJOR,      'y', sg.Color(0, 180, 100),   sg.Color(210, 255, 210)),
            (self.PARALLEL_FIFTHS,   'x', sg.Color(150, 150, 150), sg.Color(255, 255, 255)),
            (self.TRIADS_MINOR,      'w', sg.Color(100, 0, 200),   sg.Color(215, 215, 255)),
            (self.TRIADS_DIMINISHED, 'v', sg.Color(200, 0, 100),   sg.Color(255, 215, 215)),
        ]:
            pitch_classes = 0
            mem_pitch_classes = 0
            for num_note in range(0, 12):
                value = 1 << ((num_note*7) % 12)
                if self.press_counter[num_note] > 0:
                    pitch_classes |= value
                if self.memory_counter[num_note] > 0:
                    mem_pitch_classes |= value
            for num, triad_signature in enumerate(triad_signatures):
                note_id = self.NOTES[((num*7) % 12)]
                if (mem_pitch_classes & triad_signature) == triad_signature:
                    self.model_elements[label_prefix + note_id].fill = color_on
                    self.model_elements[label_prefix + note_id].active = True
                    if (pitch_classes & triad_signature) == triad_signature:
                        self.model_elements[label_prefix + note_id].stroke = self.COLOR_BLACK
                        self.model_elements[label_prefix + note_id].stroke_width = 3
                    else:
                        self.model_elements[label_prefix + note_id].stroke = self.COLOR_GRAY
                        self.model_elements[label_prefix + note_id].stroke_width = 1
                else:
                    self.model_elements[label_prefix + note_id].stroke = self.COLOR_GRAY
                    self.model_elements[label_prefix + note_id].stroke_width = 1
                    if color_off is None:
                        self.model_elements[label_prefix + note_id].active = False
                    else:
                        self.model_elements[label_prefix + note_id].fill = color_off

    def update(self):
        current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        super().update(current_timestamp)

        for num_note in range(0, 12):
            note_id = self.NOTES[num_note]
            if self.memory_counter[num_note] > 0:
                self.model_elements[note_id].stroke = self.COLOR_BLACK
                self.model_elements[note_id].stroke_width = 2
                self.model_elements[note_id].active = True
            else:
                self.model_elements[note_id].stroke = self.COLOR_GRAY
                self.model_elements[note_id].stroke_width = 1
                self.model_elements[note_id].active = False

        self.update_triads()

    def press(self, num_key, channel, action=True):
        current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        num_key, num_octave, num_note, note_id = super().press(num_key, channel, action, current_timestamp)

        num_octave = num_key // 12
        num_note = (num_key*7)%12 % 12
        note_id = self.NOTES[num_note]

        if self.press_counter[num_note] > 0:
            self.model_elements[note_id].fill = COLORS[channel]
            self.model_elements[note_id].active = True
        else:
            self.model_elements[note_id].fill = self.COLOR_WHITE

        self.update_triads()

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
hexagonal = HexLayout(0, piano.height + margin)
triads_circle = CircleOfTriads(hexagonal.width + margin, piano.height + margin)
chords = Chords(hexagonal.width + margin + triads_circle.width + margin, piano.height + margin)
scene = sg.Group([piano.root(), fifths.root(), hexagonal.root(), triads_circle.root(), chords.root()])

window_size = int(piano.width + margin + fifths.width + 2 * margin), int(piano.height + margin + hexagonal.height + 2 * margin)

feedback = sg.Group(fill=None, stroke=sg.Color.red)

#midi_player = RandomSoundPlayer([piano, fifths, hexagonal])
#midi_thread = Thread(target = midi_player.random_play, args = (8, 10, 0.3))
#midi_thread.start()

midi_filename = args.midi
#midi_filename = 'Bach_Fugue_BWV578.mid'
#midi_filename = 'Debussy_Arabesque_No1.mid'
if not midi_filename is None:
    midi_file_player = MidiFileSoundPlayer(os.path.join(this_dir, midi_filename), [piano, fifths, hexagonal, triads_circle, chords])
    midi_thread = Thread(target = midi_file_player.play)
    midi_thread.start()
else:
    midi_file_player = None
    midi_thread = None

midi_input = RtMidiSoundPlayer([piano, fifths, hexagonal, triads_circle, chords])

width, height = window_size
#config = pyglet.gl.Config(sample_buffers=1, samples=4)
window = pyglet.window.Window(
    width=width,
    height=height,
    resizable=True,
#    config=config,
    )

gl_prepare()

@window.event
def on_resize(width, height):
    gl_reshape(width, height)

@window.event
def on_draw():
    pyglet.gl.glEnable(pyglet.gl.GL_LINE_SMOOTH)
    pyglet.gl.glHint(pyglet.gl.GL_LINE_SMOOTH_HINT, pyglet.gl.GL_DONT_CARE)
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
    hexagonal.update()
    triads_circle.update()
    chords.update()

pyglet.clock.schedule_interval(update, 1./60, window)

pyglet.app.run()

pyglet.clock.schedule_interval(update, 0, window) # Specifying an interval of 0 prevents the function from being called again

if midi_thread:
    midi_thread.join()
    print("All threads finished")
