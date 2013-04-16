# -*- coding: utf-8 -*-

"""
scenegraph.element.text
"""


# imports ####################################################################

from math import hypot, degrees, atan2, modf, log

from ...font import Face
from ...opengl.utils import create_texture

from .._common import _u
from ..transform import Translate, Rotate, Scale, TransformList, Pixels
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
	
	def _aabbox(self, transforms, inheriteds):
		return self._text_bbox.aabbox(transforms + [Translate(self._anchor())], inheriteds)
	
	def _render(self, transforms, inheriteds):
		font_size = self.font_size
		font_face = self.font_face
		x_anchor = self._anchor()
		
		o  = transforms.project()
		ux = transforms.project(1, 0, 0)
		xx, xy, xz = tuple(uxi-oi for oi, uxi in zip(o, ux))
		
		scale = 1. / hypot(xx, xy)
		c, s = xx*scale, xy*scale
		angle = degrees(atan2(xy, xx))
		
		self._ws = [0]
		
		vector = font_size * scale > self._VECTOR_L
		vector = vector or (self.stroke is not None) or (self.fill is None)
		
		X0, Y0, _ = transforms.unproject(x_anchor)
		
		if vector:
			X, Y = 0., 0.
		else:
			(X, X0), (Y, Y0) = modf(X0), modf(Y0)
		
		letters = Group(
			transform=[
				Translate(self.x-(self._text_bbox.x-self.stroke_width/2.),
				          self.y-(self._text_bbox.y-self.stroke_width/2.)),
				Scale(1/scale),
				Rotate(angle),
			],
			fill_opacity=1., stroke_opacity=1.,
			stroke_width=self.stroke_width * scale
		)
		
		for uc in self.text:
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
				font_face.set_transform(c, s, Xf, Yf, scale)
				if vector:
					(Xc, Yc), (W, H), (dX, dY), outline = font_face.outline(uc)
					letter = Path(d=outline)
				else:
					(Xc, Yc), (W, H), (dX, dY), data = font_face.render(uc)
					letter = Rectangle(x=Xc, y=Yc, width=W, height=H,
					                   fill=_Texture(create_texture(W, H, data)))
				self._letters_cache[key] = letter, (Xc, Yc), (W, H), (dX, dY)

			if W > 0 and H > 0:
				letters.children.append(Use(letter, x=Xi, y=Yi))

			X += dX
			Y += dY
			self._ws.append(hypot(X, Y)/scale)
		
		filler = Rectangle(
			x=self.x, y=self.y,
			transform=[
				Scale(scale), Rotate(-angle),
				Translate(self._text_bbox.x-self.stroke_width/2.-self.x,
				          self._text_bbox.y-self.stroke_width/2.-self.y),
			],
			width=self._text_bbox.width+self.stroke_width,
			height=self._text_bbox.height+self.stroke_width,
			mask=letters,
			stroke=None,
		)
		
		_transforms = transforms + [Translate(x_anchor),
		                            Scale(1/scale), Rotate(angle)]
		with Pixels(X0, Y0):
			if self.fill:
				letters.fill, letters.stroke = Color.white, None
				filler.fill = self.fill
				filler.fill_opacity = self.fill_opacity
				filler.render(_transforms, inheriteds)
			if self.stroke:
				letters.fill, letters.stroke = None, Color.white
				filler.fill = self.stroke
				filler.fill_opacity = self.stroke_opacity
				filler.render(_transforms, inheriteds)
	
	
	def index(self, x, y=0, z=0):
		"""index of the char at x (local coordinates)."""
		for i, w in enumerate(self._ws):
			if x < w: break
		return i-1
	
	
	def _hit_test(self, x, y, z, transforms):
		x, y, z = self._text_bbox.project(x, y, z)
		return self._text_bbox._hit_test(x, y, z, transforms)
	
	def _xml_content(self, defs):
		return self.text
