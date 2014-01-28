# -*- coding: utf-8 -*-

"""
scenegraph.element
"""

# imports ####################################################################

from weakref import WeakValueDictionary as _weakdict

from ...opengl.utils import OffscreenContext
from .._common import _Element
from ..paint import Color, _Texture, _MaskContext
from ..transform import TransformList, Translate, Scale


# element ####################################################################

_elements_by_id = _weakdict()

def _id(element):
	element_id = getattr(element, "_id", "%X" % id(element))
	_elements_by_id[element_id] = element
	return element_id	

def get_element_by_id(element_id):
	return _elements_by_id[element_id]


_ATTRIBUTES = [
	"id", "href",
	"x", "y",
	"width", "height",
	"r", "rx", "ry",
	"cx", "cy",
	"points",
	"x1", "x2", "y1", "y2",
	"opacity", "color",
	"fill", "fill_opacity", "fill_rule",
	"stroke", "stroke_opacity", "stroke_width",
	"stroke_linecap", "stroke_linejoin", "stroke_miterlimit",
	"stroke_dasharray", "stroke_dashoffset",
	"font_family", "font_weight", "font_style", "font_size",
	"text_anchor",
	"transform",
	"clip_path",
	"mask",
	"d",
]

_INHERITEDS = {
	"color":             Color.black,
	"fill":              Color.black,
	"fill_opacity":      1.,
	"fill_rule":         'nonzero',
	"stroke":            Color.none,
	"stroke_opacity":    1.,
	"stroke_width":      1,
	"stroke_linecap":    'butt',
	"stroke_linejoin":   'miter',
	"stroke_miterlimit": 4.,
	"stroke_dasharray":  None,
	"stroke_dashoffset": 0.,
	"font_family":       'sans-serif',
	"font_weight":       'normal',
	"font_style":        'normal',
	"font_size":         10,
	"text_anchor":       'start',
}


class Element(_Element):
	x, y = 0, 0

	_transform_list = None

	opacity = 1.
	clip_path = None
	mask = None
	
	_state_attributes = _Element._state_attributes + list(_INHERITEDS) + [
		"x", "y", "transform",
		"opacity", "clip_path", "mask"
	]
	
	def _get_transform(self):
		return self._transform_list
	def _set_transform(self, transform):
		self._transform_list = TransformList(transform)
	transform = property(_get_transform, _set_transform)
	
	def __init__(self, **attributes):
		self._attributes = set()
		self._inheriteds = _INHERITEDS
		for attribute in attributes:
			setattr(self, attribute, attributes[attribute])
		if self.transform is None:
			self.transform = []
	
	def __setattr__(self, attribute, value):
		if attribute in _ATTRIBUTES:
			self._attributes.add(attribute)
		super(Element, self).__setattr__(attribute, value)

	def __delattr__(self, attribute):
		super(Element, self).__delattr__(attribute)
		if attribute in _ATTRIBUTES:
			self._attributes.remove(attribute)
	
	def __getattr__(self, attribute):
		if attribute in _INHERITEDS:
			return self._inheriteds[attribute]
		try:
			return super(Element, self).__getattr__(attribute)
		except AttributeError:
			return super(Element, self).__getattribute__(attribute)
	
	def _inherit(self, inheriteds):
		self._inheriteds = inheriteds
		return dict((attr, getattr(self, attr)) for attr in _INHERITEDS)
	
	@property
	def id(self):
		self._attributes.add("id")
		return _id(self)
	
	@property
	def attributes(self):
		return (name for name in _ATTRIBUTES if name in self._attributes)

	# transformations
	
	@property
	def _transform(self):
		if (self.x, self.y) == (0., 0.):
			transform = self.transform
		else:
			transform = self.transform + [Translate(self.x, self.y)]
		return transform
	
	def project(self, x=0, y=0):
		return self._transform.project(x, y)
	
	
	# axis-aligned bounding box
	
	def aabbox(self, transforms=TransformList(), inheriteds=_INHERITEDS):
		inheriteds = self._inherit(inheriteds)
		return self._aabbox(transforms + self._transform, inheriteds)
	
	def _aabbox(self, transforms, inheriteds):
		raise NotImplementedError
	
	def _units(self, elem, attr, default="userSpaceOnUse"):
		units = getattr(elem, attr, default)
		if units == "userSpaceOnUse":
			transform = []
		elif units == "objectBoundingBox":
			(x_min, y_min), (x_max, y_max) = self.aabbox()
			transform = [Translate(x_min, y_min), Scale(x_max-x_min, y_max-y_min)]
		else:
			raise ValueError("unknown units %s" % units)
		return self.transform + transform
	
	
	# rendering
	
	def _color(self, color):
		if color == Color.current:
			return self.color
		return color
	
	def render(self, transforms=TransformList(), inheriteds=_INHERITEDS,
	                 clipping=True, masking=True, opacity=True):
		inheriteds = self._inherit(inheriteds)
		
		if (clipping and self.clip_path) or (masking and self.mask):
			if clipping and self.clip_path:
				clipping = False
				mask, units = self.clip_path, "clipPathUnits"
			else:
				masking = False
				mask, units = self.mask, "maskContentUnits"
			
			mask_transforms = self._units(mask, units)
			with OffscreenContext(mask.aabbox(transforms+mask_transforms),
			                      (0., 0., 0., 0.)) as ((x, y), (width, height),
			                                            mask_texture_id):
				if mask_texture_id:
					mask.render(transforms+mask_transforms)
			
			with _MaskContext((x, y), (width, height), mask_texture_id):
				self.render(transforms, inheriteds,
				            clipping=clipping, masking=masking, opacity=opacity)
		
		elif opacity and self.opacity < 1.:
			with OffscreenContext(self.aabbox(transforms, inheriteds)) as \
			     ((x, y), (width, height), elem_texture_id):
				if elem_texture_id:
					self.render(transforms, inheriteds,
					            clipping=clipping, masking=masking, opacity=False)
			
			Rectangle(x=x, y=y, width=width, height=height,
			          fill=_Texture(elem_texture_id),
			          fill_opacity=self.opacity).render()
		
		else:
			self._render(transforms + self._transform, inheriteds)
	
	def _render(self, transforms, inheriteds):
		raise NotImplementedError
	
	
	# picking 
	
	def _hit_test(self, x, y, transforms):
		return False
	
	def pick(self, x=0, y=0, transforms=TransformList()):
		p = x, y = self.project(x, y)
		transforms = transforms + self._transform
		hits = [([self], p)] if self._hit_test(x, y, transforms) else []
		hits += [([self] + e, p) for e, p in self._pick_content(x, y, transforms)]
		return hits
		
	def _pick_content(self, x, y, transforms):
		return []


# elements ###################################################################

from .use import Use
from .group  import Group
from .rectangle import Rectangle
from .circle import Circle
from .ellipse import Ellipse
from .line import Line
from .polyline import Polyline
from .polygon import Polygon
from .path import Path
from .text import Text
from .image import Image
