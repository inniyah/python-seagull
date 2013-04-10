# -*- coding: utf-8 -*-

# imports ####################################################################

from sys import platform as _platform

if _platform == "darwin":
	from ._cocoa import get_font
else:
	raise RuntimeError("unsupported system for fonts: '%s'" % _system)


# constants ##################################################################

SERIF_FONT_FAMILY = get_font("Times")
SANS_FONT_FAMILY  = get_font("Lucida Grande")
MONO_FONT_FAMILY  = get_font("Monaco")


__all__ = [
	"get_font",
	"SERIF_FONT_FAMILY",
	"SANS_FONT_FAMILY",
	"MONO_FONT_FAMILY",
]
