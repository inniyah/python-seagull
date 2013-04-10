# -*- coding: utf-8 -*-

"""
scenegraph.element.path
"""


# imports ####################################################################

from struct import pack
from math import log, floor, sqrt

from . import Element
from ._path import (_cubic, _quadric, _arc, _stroke,
                    _evenodd_hit, _nonzero_hit, _stroke_hit, _bbox)


# flattening #################################################################

def _flatten(path_data, du2=1.):
	"""discretize path into straight segments."""
	paths = []
	path = []
	joins = []
	
	path_data_iter = iter(path_data)
	def next_d():
		return next(path_data_iter)
	
	pn = p0 = (0., 0.)
	cn = None
	for c in path_data_iter:
		x0, y0 = p0
		xn, yn = pn
		
		if c.islower():
			def next_p():
				dx, dy = next_d()
				return (x0+dx, y0+dy)
			def next_x():
				dx = next_d()
				return x0+dx
			def next_y():
				dy = next_d()
				return y0+dy
			c = c.upper()
		else:
			next_x = next_y = next_p = next_d
		
		if c == 'M':
			p1 = next_p()
			if path:
				paths.append((path, False, joins))
			path = [p1]
			joins = []
			
			pn, p0 = p0, p1

		elif c in "LHV":
			if c == 'L':
				p1 = next_p()
			elif c == 'H':
				p1 = (next_x(), y0)
			elif c == 'V':
				p1 = (x0, next_y())
			path.append(p1)
			pn, p0 = p0, p1
		
		elif c in "CS":
			if c == 'C':
				p1 = next_p()
			else: # 'S'
				p1 = (2.*x0-xn, 2*y0-yn) if cn in "CS" else p0
			p2, p3 = next_p(), next_p()
			path += _cubic(p0, p1, p2, p3, du2)
			pn, p0 = p2, p3
		
		elif c in 'QT':
			if c == 'Q':
				p1 = next_p()
			else: # 'T'
				p1 = (2.*x0-xn, 2*y0-yn) if cn in "QT" else p0
			p2 = next_p()
			path += _quadric(p0, p1, p2, du2)
			pn, p0 = p1, p2
		
		elif c == 'A':
			rs, phi, flags = next_d(), next_d(), next_d()
			p1 = next_p()
			path += _arc(p0, rs, phi, flags, p1, du2)
			pn, p0 = p0, p1
		
		elif c == 'Z':
			x1, y1 = p1 = path[0]
			dx, dy = x1-x0, y1-y0
			if dx*dx+dy*dy > du2:
				path.append(p1)
			paths.append((path, True, joins))
			path = []
			joins = []
			pn, p0 = p0, p1
		
		cn = c
		joins.append(len(path)-1)
		
	if path:
		paths.append((path, False, joins))

	return paths


# utils ######################################################################

_WIDTH_LIMIT = 1.
_SCALE_STEP  = 1.2

def _du2(transforms):
	"""square of the size of a pixel in local coordinates."""
	x, y, z = tuple(x-o for o, x in zip(transforms.project(),
	                                    transforms.project(1.)))
	return x*x+y*y+z*z

def _scale_index(du2, scale_step=_SCALE_STEP):
	"""log discretization of the scale suitable as key for hashing cache."""
	return -int(floor(log(du2, scale_step)/2.))


def _c_array(points):
	"""turn list of 2-tuple into c array of floats."""
	n = len(points)
	return n, pack("%df" % (2*n), *[u for point in points for u in point])


def _strip_range(stop):
	"""sort verticies in triangle strip order, i.e. 0 -1 1 -2 2 ..."""
	i = 0
	while i < stop:
		i += 1
		v, s = divmod(i, 2)
		yield v*(s*2-1)


def _join_strips(strips):
	"""concatenate strips"""
	strip = next(strips, [])
	for s in strips:
		if len(strip) % 2 == 1:
			strip += [strip[-1], s[0], s[0]]
		else:
			strip += [strip[-1], s[0]]
		strip += s
	return strip


# path #######################################################################

class Path(Element):
	tag = "path"
	
	_state_attributes = Element._state_attributes + [
		"d",
	]
	
	_bbox = (0., 0.), (0., 0.)
	
	_path_state   = None
	_fill_state   = None
	_stroke_state = None
	
	
	def _paths(self, du2=1.):
		path_state = list(self.d)
		if path_state != self._path_state:
			self._paths_cache = dict()
			self._path_state = path_state

		scale_index = _scale_index(du2)
		try:
			paths = self._paths_cache[scale_index]
		except KeyError:
			paths = _flatten(self.d, du2)
			self._paths_cache[scale_index] = paths
			if scale_index == max(self._paths_cache):
				self._bbox = _bbox(path for (path, _, _) in paths)
		return paths
		
	def _fills(self, du2=1.):
		fill_state = list(self.d)
		if fill_state != self._fill_state:
			self._fills_cache = dict()
			self._fill_state = fill_state
		
		scale_index = _scale_index(du2)
		try:
			fills = self._fills_cache[scale_index]
		except KeyError:
			paths = self._paths(du2)
			fills = _join_strips([path[i] for i in _strip_range(len(path))]
			                     for path, _, _ in paths)
			fills = _c_array(fills), fills
			self._fills_cache[scale_index] = fills
		return fills
	
	def _strokes(self, du2=1.):
		stroke_state = (list(self.d), self.stroke_width, self.stroke_linecap,
		                              self.stroke_linejoin, self.stroke_miterlimit)
		if stroke_state != self._stroke_state:
			self._stroke_cache = dict()
			self._stroke_state = stroke_state
		
		scale_index = _scale_index(du2)
		try:
			strokes, opacity_correction = self._stroke_cache[scale_index]
		except KeyError:
			paths = self._paths(du2)
			
			# better thin stroke rendering
			du = sqrt(du2)
			adapt_width = self.stroke_width / du
			if adapt_width < _WIDTH_LIMIT:
				width = du
				opacity_correction = adapt_width
			else:
				width = self.stroke_width
				opacity_correction = 1.
			
			# strokes
			strokes = _join_strips(_stroke(path, closed, joins, width,
			                               self.stroke_linecap, du,
			                               self.stroke_linejoin,
			                               self.stroke_miterlimit)
			                       for path, closed, joins in paths)
			strokes = _c_array(strokes), strokes
			self._stroke_cache[scale_index] = strokes, opacity_correction
		
		return strokes, opacity_correction
	
	
	def _aabbox(self, transforms, inheriteds):
		du2 = _du2(transforms)
		
		points = []
		if self.fill:
			_, fills = self._fills(du2)
			if fills:
				points.append(transforms.unproject(*p)[:2] for p in fills)
		if self.stroke and self.stroke_width > 0.:
			(_, strokes), _ = self._strokes(du2)
			if strokes:
				points.append(transforms.unproject(*p)[:2] for p in strokes)
		
		return _bbox(points)
	
	
	def _render(self, transforms, inheriteds):
		du2 = _du2(transforms)
		origin = self.x, self.y
		
		fill = self._color(self.fill)
		if fill:
			fills, _ = self._fills(du2)
			paint = {
				"nonzero": fill.paint_nonzero,
				"evenodd": fill.paint_evenodd,
			}[self.fill_rule]
			paint(self.fill_opacity, fills, origin, self._bbox)
		
		stroke = self._color(self.stroke)
		if stroke and self.stroke_width > 0.:
			(strokes, _), correction = self._strokes(du2)
			opacity = self.stroke_opacity * correction
			margin = self.stroke_width/2. / correction
			margin *= max(1., self.stroke_miterlimit)
			stroke.paint_one(opacity, strokes, origin, self._bbox, margin+1.)
	
	
	def _hit_test(self, x, y, z, transforms):
		du2 = _du2(transforms)

		if self.fill:
			(x_min, y_min), (x_max, y_max) = self._bbox
			if (x_min <= x <= x_max) and (y_min <= y <= y_max):
				_, fills = self._fills(du2)
				if fills:
					fill_hit = {
						"nonzero": _nonzero_hit,
						"evenodd": _evenodd_hit,
					}[self.fill_rule]
					if fill_hit(x, y, z, fills):
						return True

		if self.stroke and self.stroke_width > 0.:
			(_, strokes), _ = self._strokes(du2)
			if strokes:
				if _stroke_hit(x, y, z, strokes):
					return True
		
		return False
