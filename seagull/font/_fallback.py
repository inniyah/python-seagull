# -*- coding: utf-8 -*-

# imports ####################################################################

import os


# utils ######################################################################

_CONTRIBS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                              "..", "..",
                                              "contribs", "freefont-20120503"))

_FONTS = {
	"serif":      os.path.join(_CONTRIBS_PATH, "FreeSerif.otf"),
	"sans-serif": os.path.join(_CONTRIBS_PATH, "FreeSans.otf"),
	"mono":       os.path.join(_CONTRIBS_PATH, "FreeMono.otf"),
}

def get_font(family):
	return _FONTS[family]
