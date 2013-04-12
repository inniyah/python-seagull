# -*- coding: utf-8 -*-

# imports ####################################################################

import os

from sys import platform as _platform

if _platform == "darwin":
	try:
		from ._cocoa import _get_font
	except ImportError:
		pass

try:
	_get_font
except NameError:
	def _get_font(family, bold, italic):
		raise LookupError


# constants ##################################################################

_CONTRIBS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                              "..", "..",
                                              "contribs", "freefont-20120503"))

_FALLBACK_FONTS = {
	"sans-serif": {
		(False, False): os.path.join(_CONTRIBS_PATH, "FreeSans.otf"),
		(False, True):  os.path.join(_CONTRIBS_PATH, "FreeSansOblique.otf"),
		(True,  False): os.path.join(_CONTRIBS_PATH, "FreeSansBold.otf"),
		(True,  True):  os.path.join(_CONTRIBS_PATH, "FreeSansBoldOblique.otf"),
	},
	"serif": {
		(False, False): os.path.join(_CONTRIBS_PATH, "FreeSerif.otf"),
		(False, True):  os.path.join(_CONTRIBS_PATH, "FreeSerifItalic.otf"),
		(True,  False): os.path.join(_CONTRIBS_PATH, "FreeSerifBold.otf"),
		(True,  True):  os.path.join(_CONTRIBS_PATH, "FreeSerifBoldItalic.otf"),
	},
	"mono": {
		(False, False): os.path.join(_CONTRIBS_PATH, "FreeMono.otf"),
		(False, True):  os.path.join(_CONTRIBS_PATH, "FreeMonoOblique.otf"),
		(True,  False): os.path.join(_CONTRIBS_PATH, "FreeMonoBold.otf"),
		(True,  True):  os.path.join(_CONTRIBS_PATH, "FreeMonoBoldOblique.otf"),
	},
}


# font lookup ################################################################


def _get_fallback_font(family, bold=False, italic=False):
	return _FALLBACK_FONTS[family][bold, italic], 0


def get_font(families, weight="normal", style="normal"):
	bold   = weight in ["bold", "bolder", "600", "700", "800", "900"]
	italic = style in ["italic", "oblique"]
	families = [family.strip() for family in families.split(',')] + ["sans-serif"]
	font_name, index = None, 0
	for font_getter in [_get_font, _get_fallback_font]:
		for family in families:
			try:
				font_name, index = font_getter(family, bold, italic)
			except LookupError:
				continue
			break
		else:
			continue
		break
	return font_name, index


__all__ = [
	"get_font",
]
