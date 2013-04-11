# -*- coding: utf-8 -*-


# imports ####################################################################

from CoreText import (
	CTFontCollectionCreateFromAvailableFonts,
	CTFontCollectionCreateMatchingFontDescriptors,
	kCTFontFamilyNameAttribute,
	kCTFontURLAttribute,
	kCTFontStyleNameAttribute,
)


# fonts ######################################################################

_font_collection  = CTFontCollectionCreateFromAvailableFonts({})
_font_descriptors = CTFontCollectionCreateMatchingFontDescriptors(_font_collection)

_FONTS = {
	font[kCTFontFamilyNameAttribute]: str(font[kCTFontURLAttribute].path())
	for font in _font_descriptors
	if font[kCTFontStyleNameAttribute] == "Regular"
}

_FALLBACKS = {
	"serif":      "Times",
	"sans-serif": "Lucida Grande",
	"mono":       "Monaco",
}

for _fallback in _FALLBACKS:
	_FONTS[_fallback] = _FONTS[_FALLBACKS[_fallback]]


# utils ######################################################################

def get_font(family):
	return _FONTS[family]
