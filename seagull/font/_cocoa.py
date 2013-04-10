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
_font_families = dict(
	(font_descriptor[kCTFontFamilyNameAttribute],
	 font_descriptor[kCTFontURLAttribute])
	for font_descriptor in _font_descriptors
	if font_descriptor[kCTFontStyleNameAttribute] == "Regular"
)


# utils ######################################################################

def get_font(family):
	path = _font_families[family].path()
	return str(path)
