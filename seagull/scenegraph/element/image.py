# -*- coding: utf-8 -*-

"""
scenegraph.element.image
"""


# imports ####################################################################

from os.path import abspath

try:
	from PIL import Image as _Image
except ImportError:
	class _Image:
		size = (0, 0)
		mode = "RGBA"
		@classmethod
		def open(klass, href):
			return _Image()
		def tobytes(self):
			return b""

from ...opengl.utils import create_texture
from ..paint import Color, _Texture
from .rectangle import Rectangle


# image ######################################################################

class Image(Rectangle):
	tag = "image"
	
	_state_attributes = Rectangle._state_attributes + [
		"href",
	]
	
	fill = Color.white
	
	def __init__(self, href, width=None, height=None, **attributes):
		href = abspath(href)
		pil_image = _Image.open(href)
		if pil_image.mode not in ["RGB", "RGBA"]:
			pil_image = pil_image.convert("RGBA")
		iw, ih = pil_image.size
		if width is None:  width = iw
		if height is None: height = ih
		super(Image, self).__init__(width=width, height=height,
		                            **attributes)
		self.href = "file://%s" % href

		self._texture_args = (pil_image.size,
		                      pil_image.tobytes(),
		                      pil_image.mode)

	def _render(self, transform, inheriteds, context):
		(width, height), data, format = self._texture_args
		del self._texture_args
		
		self.fill = _Texture(create_texture(width, height, data, format),
		                     self.fill)
		self._attributes.remove("fill")
		
		self._render = super(Image, self)._render
		self._render(transform, inheriteds, context)
