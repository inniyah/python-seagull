# -*- coding: utf-8 -*-

"""
scenegraph.element.text
"""


# imports ####################################################################

from math import hypot, degrees, atan2, modf, log

from ...font import Face
from ...opengl.utils import create_texture

from .._common import _u
from ..transform import Translate, Rotate, Scale
from ..paint import _Texture, Color
from .rectangle import Rectangle
from .path import Path
from .group import Group
from .use import Use
from . import Element


# text #######################################################################


_ANGLE_STEPS = 360
_SCALE_DOUBLE_STEPS = 128
_SUBPIXEL_STEPS = 64

class Text(Element):
	tag = "text"
	
	_state_attributes = Element._state_attributes + [
		"font_family", "font_weight", "font_style", "font_size", "text"
	]
	
	_VECTOR_L = 30
	_letters_cache = {}
	_faces_cache = {}
	
	def __init__(self, text,
	             **attributes):
		super(Text, self).__init__(**attributes)

		self._text_bbox = Rectangle()
		self._ws = []

		self.text = text
		
		# TODO: handle list of coordinates
		if isinstance(self.x, list):
			self.x = self.x[0]
		if isinstance(self.y, list):
			self.y = self.y[0]
	
		
	def _update_text_bbox(self):
		(x, y), (width, height) = self.font_face.get_bbox(self.text)
		self._width = width
		self._text_bbox.x, self._text_bbox.width  = x, width
		self._text_bbox.y, self._text_bbox.height = y, height
		self._text_bbox._paths() # force bbox update

	@property
	def font_face(self):
		key = (self.font_family, self.font_weight, self.font_style,
		       int(self.font_size))
		try:
			font_face = self._faces_cache[key]
		except KeyError:
			font_face = self._faces_cache[key] = Face(*key)
		return font_face

	def get_text(self):
		return _u(self._text)
	def set_text(self, text):
		self._text = text.strip()
	text = property(get_text, set_text)
	
	def _anchor(self):
		self._update_text_bbox()
		return {
			'start':   0.,
			'middle': -self._width/2.,
			'end':    -self._width,
		}[self.text_anchor]
	
	def _aabbox(self, transform, inheriteds):
		return self._text_bbox.aabbox(transform * Translate(self._anchor()), inheriteds)
	
	def _render(self, transform, inheriteds, context):
		font_size = self.font_size
		font_face = self.font_face
		
		_, (cosa, sina), _, (sx, sy) = transform.params()
		a, b = cosa*sx, sina*sy
		c, d = -b, a
		scale = hypot(a, b)
		angle = degrees(atan2(b, a))
		
		vector = font_size * scale > self._VECTOR_L
		vector = vector or (self.stroke is not None) or (self.fill is None)
		
		x_anchor = self._anchor()
		X0, Y0 = transform.project(x_anchor)
		untransform = transform.inverse()
		
		if vector:
			X, Y = 0., 0.
		else:
			(X, X0), (Y, Y0) = modf(X0), modf(Y0)
		
		letters = Group(
			transform=[Translate(x_anchor), Rotate(-angle), Scale(1/scale), Translate(-X, -Y)],
			stroke_width=self.stroke_width*scale,
		)
		self._ws = [0]
		
		up = None
		for uc in self.text:
			X += font_face.get_hkerning(up, uc)
			up = uc
			
			if vector:
				(Xf, Xi), (Yf, Yi) = (0., X), (0., Y)
			else:
				(Xf, Xi), (Yf, Yi) = modf(X), modf(Y)
				if Xf < 0: Xf, Xi = Xf+1, Xi-1
				if Yf < 0: Yf, Yi = Yf+1, Yi-1
			key = (font_face, uc, vector,
			       int(round(angle*_ANGLE_STEPS/360.)),
			       int(log(scale, 2.)*_SCALE_DOUBLE_STEPS),
			       int(Xf*_SUBPIXEL_STEPS), int(Yf*_SUBPIXEL_STEPS))
			try:
				letter, (Xc, Yc), (W, H), (dX, dY) = self._letters_cache[key]
			except KeyError:
				font_face.set_transform(a, b, c, d, Xf, Yf)
				if vector:
					(Xc, Yc), (W, H), (dX, dY), outline = font_face.outline(uc)
					letter = Path(d=outline)
				else:
					(Xc, Yc), (W, H), (dX, dY), data = font_face.bitmap(uc)
					letter = Rectangle(x=Xc, y=Yc, width=W, height=H,
					                   fill=_Texture(create_texture(W, H, data)))
				self._letters_cache[key] = letter, (Xc, Yc), (W, H), (dX, dY)

			if W > 0 and H > 0:
				letters.children.append(Use(letter, x=Xi, y=Yi))

			X += dX
			Y += dY
			x, _ = untransform.project(X+X0, Y+Y0)
			self._ws.append(x-x_anchor)
		
		if all(type(c) in [type(None), Color] for c in [self.fill, self.stroke]):
			# single pass rendering
			if not vector:
				for letter in letters.children:
					letter.element.fill.rgb = self.fill.rgb
			letters.render(transform, inheriteds, context)
		
		else:
			# multi-pass rendering if a gradient or pattern is used
			filler_x, filler_y = self.x, self.y-self._text_bbox.height
			bbox_x,   bbox_y   = (self._text_bbox.x-self.stroke_width/2. + x_anchor,
			                      self._text_bbox.y-self.stroke_width/2.)
			width,    height   = (self._text_bbox.width+self.stroke_width,
				                   self._text_bbox.height+self.stroke_width)
			
			mask = Use(letters,
				transform=[Translate(filler_x-bbox_x, filler_y-bbox_y)],
				fill_opacity=1., stroke_opacity=1.,
			)

			filler = Rectangle(
				x=filler_x, y=filler_y, width=width, height=height,
				transform=[Translate(bbox_x-filler_x, bbox_y-filler_y)],
				stroke=None,
				mask=mask,
			)
			
			for filler_fill, filler_opacity, masking in [
				(self.fill,   self.fill_opacity,   (Color.white, None)),
				(self.stroke, self.stroke_opacity, (None, Color.white))
			]:
				if filler_fill:
					filler.fill, filler.fill_opacity = filler_fill, filler_opacity
					mask.fill, mask.stroke = masking
					filler.render(transform, inheriteds, context)
	
	
	def index(self, x, y=0):
		"""index of the char at x (local coordinates)."""
		for i, w in enumerate(self._ws):
			if x < w: break
		return i-1
	
	
	def _hit_test(self, x, y, transform):
		return self._text_bbox.pick(x, y, transform*Translate(self._anchor()))
	
	
	def _xml_content(self, defs):
		text = self.text
		for old, new in [('&', '&amp;'),
		                 ('<', '&lt;'),
		                 ('>', '&gt;')]:
			text = text.replace(old, new)
		return text
