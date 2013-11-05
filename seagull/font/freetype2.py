# -*- coding: utf-8 -*-

"""freetype2."""


# imports ####################################################################

from ctypes import *
from ctypes.util import find_library


# platform libraries #########################################################

from sys import platform as _platform
if _platform == "darwin":
	# patching find_library to look into X11 libs
	X11lib = "/usr/X11/lib"
	from os import environ
	try:
		DYLD_LIBRARY_PATH = environ["DYLD_LIBRARY_PATH"]
	except KeyError:
		environ["DYLD_LIBRARY_PATH"] = X11lib
	else:
		environ["DYLD_LIBRARY_PATH"] = ":".join([DYLD_LIBRARY_PATH,
		                                         X11lib])

class FreetypeWrapper(object):
	def __init__(self, ft):
		self.ft = ft
	def __getattr__(self, name):
		return getattr(self.ft, "FT_%s" % name)

FT = FreetypeWrapper(cdll.LoadLibrary(find_library("freetype")))

if _platform == "darwin":
	try:
		environ["DYLD_LIBRARY_PATH"] = DYLD_LIBRARY_PATH
		del DYLD_LIBRARY_PATH
	except NameError:
		del environ["DYLD_LIBRARY_PATH"]


# types ######################################################################

Int = c_int
Short = c_short
Long = c_long
UInt = c_uint
UShort = c_ushort
String = c_char

Fixed = c_long
Pos = c_long


class Vector(Structure):
	_fields_ = [("x", Pos),
	            ("y", Pos)]

class Matrix(Structure):
	_fields_ = [("xx", Fixed),
	            ("xy", Fixed),
	            ("yx", Fixed),
	            ("yy", Fixed)]


class Bitmap(Structure):
	_fields_ = [("rows", c_int),
	            ("width", c_int),
	            ("pitch", c_int),
	            ("buffer", POINTER(c_ubyte)), #c_void_p),
	            ("num_grays", c_short),
	            ("pixel_mode", c_char),
	            ("palette_mode", c_char),
	            ("palette", c_void_p)]

class Outline(Structure):
	_fields_ = [("n_contours", c_short),
	            ("n_points", c_short),
	            ("points", POINTER(Vector)),
	            ("tags", POINTER(c_byte)),
	            ("contours", POINTER(c_short)),
	            ("flags", c_int)]

class Size_Metrics(Structure):
	_fields_ = [("x_ppem", UShort),
	            ("y_ppem", UShort),
	            ("x_scale", Fixed),
	            ("y_scale", Fixed),
	            ("ascender", Pos),
	            ("descender", Pos),
	            ("height", Pos),
	            ("max_advance", Pos)]

class Bitmap_Size(Structure):
	_fields_ = [("height", Short),
	            ("width", Short),
	            ("size", Pos),
	            ("x_ppem", Pos),
	            ("y_ppem", Pos)]

class BBox(Structure):
	_fields_ = [("xMin", Pos),
	            ("yMin", Pos),
	            ("xMax", Pos),
	            ("yMax", Pos)]

class Glyph_Metrics(Structure):
	_fields_ = [("width", Pos),
	            ("height", Pos),
	            ("horiBearingX", Pos),
	            ("horiBearingY", Pos),
	            ("horiAdvance", Pos),
	            ("vertBearingX", Pos),
	            ("vertBearingY", Pos),
	            ("vertAdvance", Pos)]


Generic_Finalizer = CFUNCTYPE(c_void_p, c_void_p)
class Generic(Structure):
	_fields_ = [("data", c_void_p),
	            ("finalizer", Generic_Finalizer)]


class Glyph_Format(c_int):
	def __repr__(self):
		v = self.value
		return "".join(chr((v >> 8*i) & 255) for i in reversed(range(4)))

Encoding = c_int # enum

SubGlyph = c_void_p # POINTER(SubGlyphRec)
Slot_Internal = c_void_p # POINTER(Slot_InternalRec)
Size_Internal = c_void_p # POINTER(Size_InternalRec)


class CharMapRec(Structure): pass
CharMap = POINTER(CharMapRec)

class GlyphSlotRec(Structure): pass
GlyphSlot = POINTER(GlyphSlotRec)

class SizeRec(Structure): pass
Size = POINTER(SizeRec)

class FaceRec(Structure): pass
Face = POINTER(FaceRec)


Library = c_void_p


CharMapRec._fields_ = [
	("face", Face),
	("encoding", Encoding),
	("platform_id", UShort),
	("encoding_id", UShort)
]

GlyphSlotRec._fields_ = [
	("library", Library),
	("face", Face),
	("next", GlyphSlot),
	("reserved", UInt),
	("generic", Generic),
	("metrics", Glyph_Metrics),
	("linearHoriAdvance", Fixed),
	("linearVertAdvance", Fixed),
	("advance", Vector),
	("format", Glyph_Format),
	("bitmap", Bitmap),
	("bitmap_left", Int),
	("bitmap_top", Int),
	("outline", Outline),
	("num_subglyphs", UInt),
	("subglyphs", SubGlyph),
	("control_data", c_void_p),
	("control_len", c_long),
	("lsb_delta", Pos),
	("rsb_delta", Pos),
	("other", c_void_p),
	("internal", Slot_Internal),
]

SizeRec._fields_ = [
	("face", Face),
	("generic", Generic),
	("metrics", Size_Metrics),
	("internal", Size_Internal),
]

FaceRec._fields_ = [
	("num_faces", Long),
	("face_index", Long),
	("face_flags", Long),
	("style_flags", Long),
	("num_glyphs", Long),
	("family_name", POINTER(String)),
	("style_name", POINTER(String)),
	("num_fixed_sizes", Int),
	("available_sizes", POINTER(Bitmap_Size)),
	("num_charmaps", Int),
	("charmaps", POINTER(CharMap)),
	("generic", Generic),
	("bbox", BBox),
	("unit_per_EM", UShort),
	("ascender", Short),
	("descender", Short),
	("height", Short),
	("max_advance_width", Short),
	("max_advance_height", Short),
	("underline_position", Short),
	("underline_thickness", Short),
	("glyph", GlyphSlot),
	("size", Size),
	("charmap", CharMap),
]


# constants ##################################################################

LOAD_DEFAULT =                     0x0
LOAD_NO_SCALE =                    0x1
LOAD_NO_HINTING =                  0x2
LOAD_RENDER =                      0x4
LOAD_NO_BITMAP =                   0x8
LOAD_VERTICAL_LAYOUT =             0x10
LOAD_FORCE_AUTOHINT =              0x20
LOAD_CROP_BITMAP =                 0x40
LOAD_PEDANTIC =                    0x80
LOAD_IGNORE_GLOBAL_ADVANCE_WIDTH = 0x200
LOAD_NO_RECURSE =                  0x400
LOAD_IGNORE_TRANSFORM =            0x800
LOAD_MONOCHROME =                  0x1000
LOAD_LINEAR_DESIGN =               0x2000

[
	PIXEL_MODE_NONE,
	PIXEL_MODE_MONO,
	PIXEL_MODE_GRAY,
	PIXEL_MODE_GRAY2,
	PIXEL_MODE_GRAY4,
	PIXEL_MODE_LCD,
	PIXEL_MODE_LCD_V,
	PIXEL_MODE_MAX
] = [bytes([i]) for i in range(8)]

[
	RENDER_MODE_NORMAL,
	RENDER_MODE_LIGHT,
	RENDER_MODE_MONO,
	RENDER_MODE_LCD,
	RENDER_MODE_LCD_V,
	RENDER_MODE_MAX
] = range(6)

[
	KERNING_DEFAULT,
	KERNING_UNFITTED,
	KERNING_UNSCALED,
] = range(3)

def LOAD_TARGET_(x):
	return ((x) & 15) << 16

LOAD_TARGET_NORMAL = LOAD_TARGET_(RENDER_MODE_NORMAL )
LOAD_TARGET_LIGHT  = LOAD_TARGET_(RENDER_MODE_LIGHT  )
LOAD_TARGET_MONO   = LOAD_TARGET_(RENDER_MODE_MONO   )
LOAD_TARGET_LCD    = LOAD_TARGET_(RENDER_MODE_LCD    )
LOAD_TARGET_LCD_V  = LOAD_TARGET_(RENDER_MODE_LCD_V  )

def ENC_TAG(s):
	a, b, c, d = s
	return (ord(a) << 24 |
	        ord(b) << 16 |
	        ord(c) <<  8 |
	        ord(d))

ENCODING_UNICODE = ENC_TAG("unic")


# initialisation #############################################################

_library = Library()
FT.Init_FreeType(byref(_library))
