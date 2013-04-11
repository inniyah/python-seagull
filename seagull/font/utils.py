# -*- coding: utf-8 -*-

# imports ####################################################################

from sys import platform as _platform

try:
	if _platform == "darwin":
		from ._cocoa import get_font
	get_font
except:
	from ._fallback import get_font


# constants ##################################################################

SERIF_FONT_FAMILY = get_font("serif")
SANS_FONT_FAMILY  = get_font("sans-serif")
MONO_FONT_FAMILY  = get_font("mono")

__all__ = [
	"get_font",
	"SERIF_FONT_FAMILY",
	"SANS_FONT_FAMILY",
	"MONO_FONT_FAMILY",
]
