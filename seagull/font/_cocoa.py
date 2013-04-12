# -*- coding: utf-8 -*-

"""Cocoa implementation of get_font"""


# imports ####################################################################

from CoreText import (
	CTFontCollectionCreateFromAvailableFonts,
	CTFontCollectionCreateMatchingFontDescriptors,
	kCTFontFamilyNameAttribute,
	kCTFontTraitsAttribute,
	kCTFontURLAttribute,
	kCTFontSymbolicTrait,
	kCTFontItalicTrait,
	kCTFontBoldTrait,
)


# fonts ######################################################################

_font_collection  = CTFontCollectionCreateFromAvailableFonts({})
_font_descriptors = CTFontCollectionCreateMatchingFontDescriptors(_font_collection)

_FONTS = {}
_FONT_NAMES = {}
for _font in _font_descriptors:
	family = _font[kCTFontFamilyNameAttribute]
	_fonts = _FONTS.get(family, {})
	_traits = _font[kCTFontTraitsAttribute]
	_bold =   bool(_traits[kCTFontSymbolicTrait] & kCTFontBoldTrait)
	_italic = bool(_traits[kCTFontSymbolicTrait] & kCTFontItalicTrait)
	_font_name = _font[kCTFontURLAttribute].path()
	_key = _italic, _bold
	_fonts[_key] = _font_name
	_names = _FONT_NAMES.get(_font_name, [])
	_names.append(_key) # TODO: no idea how to retreive fonst index in dfont file
	_names.sort()       # so rely on arbitrary assunption
	_FONT_NAMES[_font_name] = _names
	_FONTS[family] = _fonts


# utils ######################################################################

def _get_font(family, bold, italic):
	key = italic, bold
	font_name = _FONTS[family][key]
	return font_name, _FONT_NAMES[font_name].index(key)
