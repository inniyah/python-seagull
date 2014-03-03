# -*- coding: utf-8 -*-

"""
scenegraph.element.path
"""


# imports ####################################################################

from collections import defaultdict
from copy import deepcopy
from math import log, floor, sqrt

from ...opengl.utils import create_vbo
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
			if (dx*dx+dy*dy)*du2 > 1.:
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

def _du2(transform):
	"""surface of a pixel in local coordinates."""
	a, b, c, d, _, _ = transform.abcdef
	return abs(a*d-b*c)


def _scale_index(du2, scale_step=_SCALE_STEP):
	"""log discretization of the scale suitable as key for hashing cache."""
	try:
		return int(floor(log(du2, scale_step)/2.))
	except:
		return None


def _strip_range(stop):
	"""sort verticies in triangle strip order, i.e. 0 -1 1 -2 2 ..."""
	i = 0
	while i < stop:
		i += 1
		v, s = divmod(i, 2)
		yield v*(s*2-1)


def _join_strips(strips):
	"""concatenate strips"""
	strips = iter(strips)
	strip = next(strips, [])
	for s in strips:
		if len(strip) % 2 == 1:
			strip += [strip[-1], s[0], s[0]]
		else:
			strip += [strip[-1], s[0]]
		strip += s
	return strip


# cache ######################################################################

def _fill_state(path):
	return path.d

def _stroke_state(path):
	return (
		path.d,
		path.stroke_width, path.stroke_miterlimit,
		path.stroke_linecap, path.stroke_linejoin,
	)

def _cache(_state):
	"""caching decorator
	
	cache is a dict maintained by path element mapping scale index to data
	the cache is cleared if the state characterized by attributes has changed
	"""
	def decorator(method):
		def decorated(path, du2=1.):
			state = _state(path)
			if state != path._states.get(method, None):
				path._caches[method] = cache = {}
				path._states[method] = deepcopy(state)
				path._bbox_du2 = 0.
			else:
				cache = path._caches[method]
			scale_index = _scale_index(du2)
			try:
				result = cache[scale_index]
			except KeyError:
				cache[scale_index] = result = method(path, du2)
			return result
		return decorated
	return decorator


# path #######################################################################

class Path(Element):
	tag = "path"
	
	_state_attributes = Element._state_attributes + [
		"d",
	]
	
	_bbox = (0., 0.), (0., 0.)
	_bbox_du2 = 0.

	def __init__(self, **attributes):
		super(Path, self).__init__(**attributes)
		self._caches = {}
		self._states = {}
	
	
	@_cache(_fill_state)
	def _paths(self, du2=1.):
		paths = _flatten(self.d, du2)
		if du2 > self._bbox_du2:
			self._bbox_du2 = du2
			self._bbox = _bbox(path for (path, _, _) in paths)
		return paths
	
	@_cache(_fill_state)
	def _fills(self, du2=1.):
		paths = self._paths(du2)
		return _join_strips([path[i] for i in _strip_range(len(path))]
		                    for path, _, _ in paths)
	
	@_cache(_fill_state)
	def _fills_data(self, du2):
		fills = self._fills(du2)
		return create_vbo(fills)
	
	
	@_cache(_stroke_state)
	def _strokes(self, du2=1.):
		paths = self._paths(du2)
		
		# better thin stroke rendering
		du = sqrt(du2)
		adapt_width = self.stroke_width * du
		if adapt_width < _WIDTH_LIMIT:
			width = 1./du
			opacity_correction = adapt_width
		else:
			width = self.stroke_width
			opacity_correction = 1.
		
		return _join_strips(_stroke(path, closed, joins, width, du,
		                            self.stroke_linecap, self.stroke_linejoin,
		                            self.stroke_miterlimit)
		                    for path, closed, joins in paths), opacity_correction
	
	@_cache(_stroke_state)
	def _strokes_data(self, du2):
		strokes, opacity_correction = self._strokes(du2)
		return create_vbo(strokes), opacity_correction
	
	
	def _aabbox(self, transform, inheriteds):
		du2 = _du2(transform)
		
		points = []
		if self.fill:
			fills = self._fills(du2)
			if fills:
				points.append(transform.project(*p) for p in fills)
		if self.stroke and self.stroke_width > 0.:
			strokes, _ = self._strokes(du2)
			if strokes:
				points.append(transform.project(*p) for p in strokes)
		
		return _bbox(points)
	
	
	def _render(self, transform, inheriteds, context):
		du2 = _du2(transform)
		origin = self.x, self.y
		
		fill = self._color(self.fill)
		if fill:
			fills = self._fills_data(du2)
			paint = {
				"nonzero": fill.paint_nonzero,
				"evenodd": fill.paint_evenodd,
			}[self.fill_rule]
			paint(self.fill_opacity, fills, transform, context, origin, self._bbox)
		
		stroke = self._color(self.stroke)
		if stroke and self.stroke_width > 0.:
			strokes, correction = self._strokes_data(du2)
			opacity = self.stroke_opacity * correction
			stroke.paint_one(opacity, strokes, transform, context, origin, self._bbox)
	
	
	def _hit_test(self, x, y, transform):
		x, y = transform.inverse().project(x, y)
		du2 = _du2(transform)
		hit = False
		
		if not hit and self.fill:
			(x_min, y_min), (x_max, y_max) = self._bbox
			if (x_min <= x <= x_max) and (y_min <= y <= y_max):
				fills = self._fills(du2)
				if fills:
					fill_hit = {
						"nonzero": _nonzero_hit,
						"evenodd": _evenodd_hit,
					}[self.fill_rule]
					hit = fill_hit(x, y, fills)

		if not hit and self.stroke and self.stroke_width > 0.:
			strokes, _ = self._strokes(du2)
			if strokes:
				hit = _stroke_hit(x, y, strokes)
		
		return [([self], (x, y))] if hit else []
