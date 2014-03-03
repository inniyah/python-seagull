# -*- coding: utf-8 -*-

"""
scenegraph.element._path

Low level path utility functions suitable for optimizations based on typing.
"""


# imports ####################################################################

from math import hypot, sqrt, pi, cos, sin, atan2, radians


# constants ##################################################################

INF = float("inf")


# geometry ###################################################################

def _line(p0, p1):
	"""equation of (p0, p1) in the ax+by+c=0 form."""
	(x0, y0), (x1, y1) = p0, p1
	dx, dy = x1-x0, y1-y0
	return dy, -dx, y0*dx-x0*dy

def _intersection(l0, l1, e=1e-6):
	"""intersection of lines."""
	a0, b0, c0 = l0
	a1, b1, c1 = l1
	w = a0*b1 - a1*b0
	x = b0*c1 - b1*c0
	y = c0*a1 - c1*a0
	if abs(w) < e: raise ZeroDivisionError
	return x/w, y/w

def _parallel(l, p):
	"""parallel to l passing by p."""
	a, b, c = l
	x, y = p
	return a, b, -(a*x+b*y)

def _h(p0, p1):
	"""distance between two points."""
	(x0, y0), (x1, y1) = p0, p1
	return hypot(x1-x0, y1-y0)

def _lerp(p0, p1, t=.5):
	(x0, y0), (x1, y1) = p0, p1
	return x0+t*(x1-x0), y0+t*(y1-y0)


# flattening #################################################################

# Bézier splines

_L2_RATIO = 4 # trade-off precision for polygons

def _casteljau(p0, p1, p2, p3, t=.5):
	"""de Casteljau subdivision of cubic Bézier curve."""
	p01, p12, p23 = _lerp(p0, p1, t), _lerp(p1, p2, t), _lerp(p2, p3, t)
	p012, p123 = _lerp(p01, p12, t), _lerp(p12, p23, t)
	p0123 = _lerp(p012, p123, t)
	return p01, p12, p23, p012, p123, p0123

def _cubic(p0, p1, p2, p3, du2):
	"""cubic Bézier spline flattenization."""
	if (p0, p2) == (p1, p3):
		return [p3]
	
	(x0, y0), (x1, y1), (x2, y2), (x3, y3) = p0, p1, p2, p3
	d1 = (x3-x0)*(y1-y0) - (y3-y0)*(x1-x0)
	d2 = (x3-x0)*(y2-y0) - (y3-y0)*(x2-x0)
	dd03 = (x3-x0)*(x3-x0)+(y3-y0)*(y3-y0)
	if (d1*d1+d2*d2)*du2 < dd03*_L2_RATIO:
		return [_lerp(p1, p2), p3]
	else:
		p01, p12, p23, p012, p123, p0123 = _casteljau(p0, p1, p2, p3)
		return _cubic(p0, p01, p012, p0123, du2) + \
		       _cubic(p0123, p123, p23, p3, du2)

def _quadric(p0, p1, p2, du2):
	"""quadric Bézier spline flattenization by transforming it to cubic."""
	return _cubic(p0, _lerp(p0, p1, 2/3.), _lerp(p1, p2, 1/3.), p2, du2)


# arc

def _arc(p0, rs, phi, flags, p1, du2):
	"""arc flatenization.
	
	implementation derived from
	<http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes>
	"""
	if p0 == p1:
		return []
	
	rx, ry = rs
	if rx == 0 or ry == 0:
		return [p1]
	rx, ry = abs(rx), abs(ry)
	
	phi = radians(phi) % pi
	c, s = cos(phi), sin(phi)

	large_arc, sweep = map(bool, flags)
	
	(x0, y0), (x1, y1) = p0, p1
	

	ux, uy = .5*(x0-x1), .5*(y0-y1)
	X, Y = c*ux+s*uy, -s*ux+c*uy
	
	X2, Y2, r2x, r2y = X*X, Y*Y, rx*rx, ry*ry
	L2 = X2/r2x + Y2/r2y
	
	if L2 > 1.:
		L = sqrt(L2)
		rx, ry = L*rx, L*ry
		r2x, r2y = L2*r2x, L2*r2y

	K = sqrt(max(0., (r2x*r2y - r2x*Y2 - r2y*X2)/(r2x*Y2+r2y*X2)))
	if large_arc == sweep:
		K = -K
	Xc, Yc = K*Y*rx/ry, -K*X*ry/rx
	
	a0 = atan2(-(Yc-Y)/ry, -(Xc-X)/rx)
	da = atan2(-(Yc+Y)/ry, -(Xc+X)/rx) - a0
	if sweep:
		if da < 0: da += 2*pi
	else:
		if da > 0: da -= 2*pi

	path = []
	xc, yc = c*Xc-s*Yc + ux+x1, s*Xc+c*Yc + uy+y1
	N = int((((r2x+r2y)*du2)**.25) * abs(da))
	for i in range(N-1):
		a = a0 + da*(i+1)/N
		X, Y = rx*cos(a), ry*sin(a)
		path.append((c*X-s*Y+xc, s*X+c*Y+yc))
	path.append(p1) # i in range(N) introduce numerical errors for p1
	
	return path


# stroking ###################################################################

# caps

def _offset(p0, p1, hw):
	if p0 == p1:
		return 0., hw
	(x0, y0), (x1, y1) = p0, p1
	dx, dy = x1-x0, y1-y0
	w = hw/hypot(dx, dy)
	return dy*w, -dx*w

def _caps_butt(p0, p1, hw, du=1, start=True):
	"""compute butt cap of width 2*hw for [p0,p1]."""
	aw, bw = _offset(p0, p1, hw)
	if start:
		x, y = p0
	else:
		x, y = p1
	return [(x+aw, y+bw), (x-aw, y-bw)]

def _caps_square(p0, p1, hw, du=1, start=True):
	"""compute square cap of width 2*hw for [p0,p1]."""
	aw, bw = _offset(p0, p1, hw)
	if start:
		x, y = p0
		return [(x+aw+bw, y+bw-aw), (x-aw+bw, y-bw-aw),
		        (x+aw,    y+bw),    (x-aw,    y-bw)]
	else:
		x, y = p1
		return [(x+aw,    y+bw),    (x-aw,    y-bw),
		        (x+aw-bw, y+bw+aw), (x-aw-bw, y-bw+aw)]

def _caps_round(p0, p1, hw, du=1, start=True):
	"""compute round cap of width 2*hw for [p0,p1]."""
	aw, bw = _offset(p0, p1, hw)
	n = int(sqrt(hw*du)) + 1 # 1/(du*hw) ~ 1 - cos(da/2) ~ daˆ2/8 at first order
	da = pi/(2*n+1)
	if start:
		x, y = p0
		n0 = n
	else:
		x, y = p1
		n0 = 0
	r = []
	for i in range(n+1):
		a = (n0-i)*da
		c, s = cos(a), sin(a)
		r += [(x+c*aw+s*bw, y+c*bw-s*aw), (x-c*aw+s*bw, y-c*bw-s*aw)]
	return r

# join

def _join_miter(p0, p1, p2, hw, du, miterlimit):
	p0a, p0b, p1a, p1b = _join_bevel(p0, p1, p2, hw, du, miterlimit)
	l0, l1 = _line(p0, p1), _line(p1, p2)
	try:
		pa = _intersection(_parallel(l0, p0a), _parallel(l1, p1a))
		pb = _intersection(_parallel(l0, p0b), _parallel(l1, p1b))
	except ZeroDivisionError:
		return [p1a, p1b]
	r = miterlimit*hw/_h(p1a, pa)
	if r < 1.:
		return [_lerp(p0a, pa, r), _lerp(p0b, pb, r),
		        _lerp(p1a, pa, r), _lerp(p1b, pb, r)]
#		return [p0a, p0b, p1a, p1b]
	else:
		return [pa, pb]

def _join_bevel(p0, p1, p2, hw, du, miterlimit):
	return _caps_butt(p0, p1, hw, start=False) + \
	       _caps_butt(p1, p2, hw)

def _join_round(p0, p1, p2, hw, du, miterlimit):
	return _caps_butt(p0, p1, hw, du, start=False) + \
	       _caps_round(p1, p2, hw, du)



# stroke

_caps = {
	'butt':   _caps_butt,
	'square': _caps_square,
	'round':  _caps_round,
}

_joins = {
	'miter': _join_miter,
	'bevel': _join_bevel,
	'round': _join_round,
}


def _enumerate_unique(path):
	previous = None
	for i, p in enumerate(path):
		if p != previous:
			yield i, p
		previous = p


def _stroke(path, closed, joins, width, du=1.,
            cap='butt', join='miter', miterlimit=4.):
	"""compute a stroke from discretized path."""
	hw = width / 2.
	_cap = _caps[cap]
	_join = _joins[join]
	stroke = []
	
	path_points = _enumerate_unique(path)
	(i0, p0) = next(path_points)
	(i1, p1) = next(path_points, (i0, p0))
	p0i, p1i = p0, p1
	
	join_indices = iter(joins)
	next_join = next(join_indices)
	while next_join < i1:
		next_join = next(join_indices)
	
	for i2, p2 in path_points:
		if i1 == next_join:
			j = _join(p0, p1, p2, hw, du, miterlimit)
			next_join = next(join_indices, 0)
		else:
			j = _join_miter(p0, p1, p2, hw, du, 1.)
		stroke += j
		i1 = i2
		p0, p1 = p1, p2
	
	if closed:
		b = e = _join(p0, p1, p1i, hw, du, miterlimit)
	else:
		b = _cap(p0i, p1i, hw, du)
		e = _cap(p0,  p1,  hw, du, start=False)
	
	return b + stroke + e


# filling ####################################################################

def _triangle_strip_hits(strip, x, y):
	"""yields hits and signs in triangles stored as strip."""
	strip_iter = iter(strip)
	p0, p1 = next(strip_iter), next(strip_iter)
	a0, b0, c0 = _line(p0, p1)
	s0, s = a0*x+b0*y+c0, 1
	for p2 in strip_iter:
		a1, b1, c1 = _line(p1, p2)
		s1 = a1*x+b1*y+c1
		a2, b2, c2 = _line(p2, p0)
		s2 = a2*x+b2*y+c2
		yield (s0*s1 > 0) and (s1*s2 > 0), s0*s > 0
		p0, p1 = p1, p2
		s0, s = s1, -s

def _evenodd_hit(x, y, fills):
	"""even/odd hit test on interior of a path."""
	in_count = 0
	for hit, _ in _triangle_strip_hits(fills, x, y):
		if hit:
			in_count += 1
	return (in_count % 2) == 1

def _nonzero_hit(x, y, fills):
	"""non-zero hit test on interior of a path."""
	in_count = 0
	for hit, positive in _triangle_strip_hits(fills, x, y):
		if hit:
			if positive:
				in_count += 1
			else:
				in_count -= 1
	return in_count != 0

def _stroke_hit(x, y, strokes):
	"""hit test on stroke of a path."""
	for hit, _ in _triangle_strip_hits(strokes, x, y):
		if hit:
			return True
	return False


def _bbox(paths):
	"""bounding box of a path."""
	x_min = y_min = +INF
	x_max = y_max = -INF
	for path in paths:
		xs, ys = zip(*path)
		x_min, x_max = min(x_min, min(xs)), max(x_max, max(xs))
		y_min, y_max = min(y_min, min(ys)), max(y_max, max(ys))
	return (x_min, y_min), (x_max, y_max)
