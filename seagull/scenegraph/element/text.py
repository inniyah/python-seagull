# -*- coding: utf-8 -*-

"""
scenegraph.element.text
"""


# imports ####################################################################

from math import hypot, degrees, atan2, modf, log

from ...font import Face
from ...font.utils import SANS_FONT_FAMILY
from ...opengl.utils import create_texture

from .._common import _u
from ..transform import Translate, Rotate, Scale, TransformList, Pixels
from ..paint import _Texture
from .rectangle import Rectangle
from .path import Path
from . import Element


# text #######################################################################


_ANGLE_STEPS = 360
_SCALE_DOUBLE_STEPS = 128
_SUBPIXEL_STEPS = 64

class Text(Element):
	tag = "text"
	
	_state_attributes = Element._state_attributes + [
		"font_family", "font_size", "text"
	]
	
	_VECTOR_L = 30
	_letters_cache = {}
	
	def __init__(self, text,
	             font_family=SANS_FONT_FAMILY,
	             font_size=10,
	             **attributes):
		super(Text, self).__init__(**attributes)
		self._font_family = font_family  # read only for now
		self._font_size = int(font_size) # idem
		self._attributes.add("font_family")
		self._attributes.add("font_size")

		self.font_face = Face(self.font_family, self.font_size)
		self._text_bbox = Rectangle()
		self._ws = []

		self.text = text
		
		# TODO: handle list of coordinates
		if isinstance(self.x, list):
			self.x = self.x[0]
		if isinstance(self.y, list):
			self.y = self.y[0]
		
	
	@property
	def font_family(self):
		return self._font_family
	
	@property
	def font_size(self):
		return self._font_size

	def get_text(self):
		return _u(self._text)
	def set_text(self, text):
		self._text = text.strip()
		(x, y), (width, height) = self.font_face.get_bbox(self.text)
		self._width = width
		self._text_bbox.x, self._text_bbox.width  = x, width
		self._text_bbox.y, self._text_bbox.height = y, height
		self._text_bbox._paths() # force bbox update
	text = property(get_text, set_text)
	
	def _anchor(self):
		return {
			'start':   0.,
			'middle': -self._width/2.,
			'end':    -self._width,
		}[self.text_anchor]
	
	def _aabbox(self, transforms, inheriteds):
		return self._text_bbox.aabbox(transforms + [Translate(self._anchor())], inheriteds)
	
	def _render(self, transforms, inheriteds):
		o  = transforms.project()
		ux = transforms.project(1, 0, 0)
		xx, xy, xz = tuple(uxi-oi for oi, uxi in zip(o, ux))
		
		scale = 1. / hypot(xx, xy)
		c, s = xx*scale, xy*scale
		angle = degrees(atan2(xy, xx))
		
		letters = []
		self._ws = [0]

		vector = self.font_size * scale > self._VECTOR_L
		vector = vector or (self.stroke is not None)
		X0, Y0, _ = transforms.unproject(self._anchor())
		if vector:
			X, Y = 0., 0.
		else:
			(X, X0), (Y, Y0) = modf(X0), modf(Y0)
		
		for uc in self.text:
			if vector:
				(Xf, Xi), (Yf, Yi) = (0., X), (0., Y)
			else:
				(Xf, Xi), (Yf, Yi) = modf(X), modf(Y)
				if Xf < 0: Xf, Xi = Xf+1, Xi-1
				if Yf < 0: Yf, Yi = Yf+1, Yi-1
			key = (self._font_family, self._font_size, uc,
			       int(round(angle*_ANGLE_STEPS/360.)),
			       int(log(scale, 2.)*_SCALE_DOUBLE_STEPS),
			       int(Xf*_SUBPIXEL_STEPS), int(Yf*_SUBPIXEL_STEPS))
			try:
				letter, (Xc, Yc), (W, H), (dX, dY) = self._letters_cache[key]
			except KeyError:
				self.font_face.set_transform(c, s, Xf, Yf, scale)
				if vector:
					(Xc, Yc), (W, H), (dX, dY), outline = self.font_face.outline(uc)
					letter = Path(d=outline, stroke=None)
				else:
					(Xc, Yc), (W, H), (dX, dY), data = self.font_face.render(uc)
					letter = Rectangle(x=Xc, y=Yc, width=W, height=H,
					                   fill=_Texture(create_texture(W, H, data)))
				self._letters_cache[key] = letter, (Xc, Yc), (W, H), (dX, dY)

			letters.append((letter, Translate(Xi, Yi)))

			X += dX
			Y += dY
			self._ws.append(hypot(X, Y)/scale)
		
		with Pixels(X0, Y0):
			for letter, translate in letters:
				letter.fill_opacity = self.fill_opacity
				if isinstance(letter, Rectangle):
					letter.fill._r, letter.fill._g, letter.fill._b = self.fill._r, self.fill._g, self.fill._b
				else:
					letter.fill = self.fill
					letter.stroke = self.stroke
					letter.stroke_opacity = self.stroke_opacity
					letter.stroke_width = self.stroke_width * scale
				translation = [translate, Translate(letter.x, letter.y)]
				with TransformList(translation):
					letter._render(transforms + TransformList([Rotate(-angle), Scale(1/scale)]) + translation, inheriteds)
	
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
