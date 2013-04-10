# -*- coding: utf-8 -*-

"""font abstraction"""


# imports ####################################################################

from itertools import chain

from ctypes import byref, string_at

from . import freetype2 as _ft2
_FT = _ft2.FT
_library = _ft2._library


# globals ####################################################################

def _on(tag):    return bool(tag & 1)
def _cubic(tag): return bool(tag & 2)


# face #######################################################################

class Face(object):
	def __init__(self, font_name, px=10):
		self.face = _ft2.Face()
		self.pen = _ft2.Vector()
		if _FT.New_Face(_library, font_name.encode(), 0, byref(self.face)) != 0:
			raise ValueError("unable to create '%s' face" % font_name)
		if px != None:
			self.set_size(px)
		self._FT = _FT # keep a ref for finalizer
	
	def __del__(self):
		try:
			self._FT.Done_Face(self.face)
		except AttributeError:
			pass
	
	
	def set_size(self, px):
		_FT.Set_Pixel_Sizes(self.face, 0, px)
	
	def set_transform(self, c=1., s=0., dx=0, dy=0, scale=1.):
		c = int(c * scale * 0x10000)
		s = int(s * scale * 0x10000)
		matrix = _ft2.Matrix()
		matrix.xx, matrix.xy = c, -s
		matrix.yx, matrix.yy = s,  c
		self.pen.x = int( dx * 64)
		self.pen.y = int(-dy * 64)
		_FT.Set_Transform(self.face, byref(matrix), byref(self.pen))
	
	def _glyph(self, uc):
		glyph_index = _FT.Get_Char_Index(self.face, ord(uc))
		_FT.Load_Glyph(self.face, glyph_index, _ft2.LOAD_DEFAULT)
		return self.face.contents.glyph.contents
	
	def get_bbox(self, text):
		self.set_transform()
		width = 0
		top, bottom = 0, 0
		for uc in text:
			glyph = self._glyph(uc)
			width += glyph.metrics.horiAdvance
			top = max(top, glyph.metrics.horiBearingY)
			bottom = min(bottom, glyph.metrics.horiBearingY - glyph.metrics.height)
		return (0., -top/64.), (width/64., (top-bottom)/64.)
	
	def render(self, uc):
		glyph = self._glyph(uc)
		
		_FT.Render_Glyph(byref(glyph), _ft2.RENDER_MODE_NORMAL)
		x, y = glyph.bitmap_left, glyph.bitmap_top
		bitmap = glyph.bitmap
		rows, columns = bitmap.rows, bitmap.pitch
		n = rows * columns
		data = string_at(bitmap.buffer, n)
		
		assert bitmap.pixel_mode == _ft2.PIXEL_MODE_GRAY
		data = bytes(chain(*([255, 255, 255, c] for c in data)))
		
		origin = x, -y
		size = columns, rows
		offset = glyph.advance.x/64., -glyph.advance.y/64.
		return origin, size, offset, data
	
	
	def outline(self, uc):
		glyph = self._glyph(uc)

		outline = glyph.outline
		
		data = []
		b = 0
		for c in range(outline.n_contours):
			e = outline.contours[c]
			
			# ensure we start with an 'on' point
			for s in range(b, e+1):
				if _on(outline.tags[s]):
					break
			
			# generate path data
			contour = []
			command, offs = 'M', []
			for i in chain(range(s, e+1), range(b, s+1)):
				point, tag = outline.points[i], outline.tags[i]
				point = (point.x/64., -point.y/64.)
				if _on(tag): # 'on' point
					contour.append(command)
					if command is 'Q' and len(offs) >= 2:
						(x0, y0) = offs[0]
						for (x1, y1) in offs[1:]:
							contour += [(x0, y0), ((x0+x1)/2, (y0+y1)/2), 'Q']
							x0, y0 = x1, y1
						contour.append((x0, y0))
					else: # 'off' point
						contour += offs
					contour.append(point)
					command, offs = 'L', []
				else:
					offs.append(point)
					command = 'C' if _cubic(tag) else 'Q'
			if contour:
				contour.append('Z')
			data += contour
			b = e+1
		
		# bbox
		bbox = _ft2.BBox()
		_FT.Outline_Get_BBox(byref(outline), byref(bbox))
		xmin, xmax = bbox.xMin/64., bbox.xMax/64.
		ymin, ymax = bbox.yMin/64., bbox.yMax/64.
		
		origin = xmin, -ymax
		size = xmax-xmin, ymax-ymin
		offset = glyph.advance.x/64., -glyph.advance.y/64.
		return origin, size, offset, data
