# -*- coding: utf-8 -*-

"""OpenGL wrapper.

Use namespace instead of prefixes for opengl functions and constants :
replace GL_CONSTANTS and glFunctions with gl.CONSTANTS (or gl._CONSTANTS when
CONSTANTS is not a valid identifier) and gl.Functions
"""


# imports ####################################################################

from OpenGL import GL as _GL


# constants ##################################################################

CONST_PREFIX = "GL_"
FUNC_PREFIX  = "gl"


# helpers ####################################################################

module_globals = globals()
__all__ = []

def export(name, value):
	module_globals[name] = value
	__all__.append(name)


# symbols ####################################################################

for symbol in dir(_GL):
	if symbol.startswith(CONST_PREFIX):
		name = symbol[len(CONST_PREFIX):]
		try:
			int(name[0])
		except ValueError:
			pass
		else:
			name = '_' + name

	elif symbol.startswith(FUNC_PREFIX):
		name = symbol[len(FUNC_PREFIX):]
		
	else:
		continue
	
	export(name, getattr(_GL, symbol))


# types ######################################################################

import ctypes
GL_TYPES = {
	"enum":     ctypes.c_uint,
	"boolean":  ctypes.c_ubyte,
	"bitfield": ctypes.c_uint,
	"byte":     ctypes.c_byte,
	"short":    ctypes.c_short,
	"int":      ctypes.c_int,
	"sizei":    ctypes.c_int,
	"ubyte":    ctypes.c_ubyte,
	"ushort":   ctypes.c_ushort,
	"uint":     ctypes.c_uint,
	"float":    ctypes.c_float,
	"clampf":   ctypes.c_float,
	"void":     None,
	"fixed":    ctypes.c_int,
	"clampx":   ctypes.c_int,
	"intptr":   ctypes.c_int,
	"sizeiptr": ctypes.c_int,
}

for name in GL_TYPES:
	export(name, GL_TYPES[name])


# clean up # symbols #########################################################

del module_globals
