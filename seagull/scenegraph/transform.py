# -*- coding: utf-8 -*-

"""
transforms
"""

# imports ####################################################################

from math import radians, cos, sin, hypot, degrees, atan2, tan

from ..opengl import gl as _gl
from ._common import _Context


# transforms #################################################################

class _Transform(_Context):
	def enter(self):
		_gl.PushMatrix()
		self.render()
		
	def exit(self):
		_gl.PopMatrix()


class Pixels(_Transform):
	def __init__(self, X=0, Y=0):
		self.O = X, Y, 0
		
	def render(self):
		_gl.LoadIdentity()
		_gl.Translate(*self.O)


def _translate(x, y, tx=0, ty=0):
	return x+tx, y+ty

def _scale(x, y, sx=1., sy=1.):
	return x*sx, y*sy
	
def _rotate(x, y, a=0.):
	a = radians(a)
	c, s = cos(a), sin(a)
	return x*c - y*s, x*s + y*c

def _shearx(x, y, ax=0.):
	t = tan(radians(ax))
	return x + t*y, y

def _sheary(x, y, ay=0.):
	t = tan(radians(ay))
	return x, y + t*x


class Translate(_Transform):
	_state_attributes = _Transform._state_attributes + [
		"tx", "ty",
	]
	
	def __init__(self, tx=0, ty=0):
		self.tx, self.ty = tx, ty

	def render(self):
		_gl.Translate(self.tx, self.ty, 0)
	
	def unproject(self, x=0, y=0):
		x, y = _translate(x, y, self.tx, self.ty)
		return x, y

	def project(self, x=0, y=0):
		x, y = _translate(x, y, -self.tx, -self.ty)
		return x, y
		
	def inverted(self):
		return Translate(-self.tx, -self.ty)
	
	@property
	def matrix(self):
		return [[1., 0., self.tx],
		        [0., 1., self.ty],
		        [0., 0.,      1.]]
	
	def __str__(self):
		return "translate(" + \
		       ",".join(str(t) for t in [self.tx, self.ty]) + \
		       ")"


class Scale(_Transform):
	_state_attributes = _Transform._state_attributes + [
		"sx", "sy",
	]
	
	def __init__(self, sx=1., sy=None):
		self.sx = sx
		self.sy = sy or sx
		
	def render(self):
		_gl.Scale(self.sx, self.sy, 1.)
	
	def unproject(self, x=0, y=0):
		x, y = _scale(x, y, self.sx, self.sy)
		return x, y

	def project(self, x=0, y=0):
		x, y = _scale(x, y, 1./self.sx, 1./self.sy)
		return x, y

	def inverted(self):
		return Scale(1./self.sx, 1./self.sy)
	
	@property
	def matrix(self):
		return [[self.sx, 0.,      0.],
		        [0.,      self.sy, 0.],
		        [0.,      0.,      1.]]
	
	def __str__(self):
		return "scale(" + \
		       ",".join(str(t) for t in [self.sx, self.sy]) + \
		       ")"

	
class Rotate(_Transform):
	_state_attributes = _Transform._state_attributes + [
		"a",
		"cx", "cy",
	]
	
	def __init__(self, a=0, cx=0, cy=0):
		self.a = a
		self.cx, self.cy = cx, cy
		
	def render(self):
		_gl.Translate(self.cx, self.cy, 0.)
		_gl.Rotate(self.a, 0., 0., 1.)
		_gl.Translate(-self.cx, -self.cy, 0.)
	
	def unproject(self, x=0, y=0):
		x, y = _translate(x, y, -self.cx, -self.cy)
		x, y = _rotate(x, y, self.a)
		x, y = _translate(x, y, self.cx, self.cy)
		return x, y

	def project(self, x=0, y=0):
		x, y = _translate(x, y, -self.cx, -self.cy)
		x, y = _rotate(x, y, -self.a)
		x, y = _translate(x, y, self.cx, self.cy)
		return x, y

	def inverted(self):
		return Rotate(-self.a, self.cx, self.cy)
	
	@property
	def matrix(self):
		a, cx, cy = radians(self.a), self.cx, self.cy
		c, s = cos(a), sin(a)
		return [[c, -s,  cx*(c-1.)-cy*s],
		        [s,  c,  cy*(c-1.)+cx*s],
		        [0., 0.,             1.]]
	
	def __str__(self):
		return "rotate(" + \
		       ",".join(str(t) for t in [self.a,
			                              self.cx, self.cy]) + \
		       ")"


class SkewX(_Transform):
	_state_attributes = _Transform._state_attributes + [
		"ax",
	]
	
	def __init__(self, ax=0.):
		self.ax = ax
	
	def render(self):
		t = tan(radians(self.ax))
		_gl.MultMatrixf([1., 0., 0., 0.,
		                 t,  1., 0., 0.,
		                 0., 0., 1., 0.,
		                 0., 0., 0., 1.])
	
	def unproject(self, x=0, y=0):
		x, y = _shearx(x, y, self.ax)
		return x, y
	
	def project(self, x=0, y=0):
		x, y = _shearx(x, y, -self.ax)
		return x, y

	def inverted(self):
		return SkewX(-self.ax)
	
	@property
	def matrix(self):
		t = tan(radians(self.ax))
		return [[1., t,  0.],
		        [0., 1., 0.],
		        [0., 0., 1.]]
	
	def __str__(self):
		return "skewX(%s)" % self.ax


class SkewY(_Transform):
	_state_attributes = _Transform._state_attributes + [
		"ay",
	]
	
	def __init__(self, ay=0.):
		self.ay = ay
	
	def render(self):
		t = tan(radians(self.ay))
		_gl.MultMatrixf([1., t,  0., 0.,
		                 0., 1., 0., 0.,
		                 0., 0., 1., 0.,
		                 0., 0., 0., 1.])

	def unproject(self, x=0, y=0):
		x, y = _sheary(x, y, self.ay)
		return x, y
	
	def project(self, x=0, y=0):
		x, y = _sheary(x, y, -self.ay)
		return x, y

	def inverted(self):
		return SkewY(-self.ay)
	
	@property
	def matrix(self):
		t = tan(radians(self.ay))
		return [[1., 0., 0.],
		        [t,  1., 0.],
		        [0., 0., 1.]]
	
	def __str__(self):
		return "skewY(%s)" % self.ay

class Matrix:
	def __init__(self, a=1., b=0., c=0., d=1., e=0., f=0.):
		self.a, self.c, self.e = a, c, e
		self.b, self.d, self.f = b, d, f

	@property
	def matrix(self):
		return [[self.a, self.c, self.e],
		        [self.b, self.d, self.f],
		        [0.,     0.,     1.]]
	
	def __mul__(self, other):
		(sa, sc, se), (sb, sd, sf), _ = self.matrix
		(oa, oc, oe), (ob, od, of), _ = other.matrix
		a, c, e = sa*oa+sc*ob, sa*oc+sc*od, sa*oe+sc*of+se
		b, d, f = sb*oa+sd*ob, sb*oc+sd*od, sb*oe+sd*of+sf
		return Matrix(a, b, c, d, e, f)
	
	def __imul__(self, other):
		(sa, sc, se), (sb, sd, sf), _ = self.matrix
		(oa, oc, oe), (ob, od, of), _ = other.matrix
		self.a, self.c, self.e = sa*oa+sc*ob, sa*oc+sc*od, sa*oe+sc*of+se
		self.b, self.d, self.f = sb*oa+sd*ob, sb*oc+sd*od, sb*oe+sd*of+sf
		return self
	
	def inverse(self):
		(a, c, e), (b, d, f), _ = self.matrix
		try:
			idet = 1./(a*d-b*c)
		except ZeroDivisionError:
			return Matrix()
		return Matrix(*(idet*u for u in (d, -b, -c, a, c*f-e*d, b*d-a*f)))

	def t(self):
		return (self.a, self.b, 0.,
		        self.c, self.d, 0.,
		        self.e, self.f, 1.)


def _params_from_matrix(a, b, c, d, e, f, error=1e-6):
	"""separate translation, rotation, shear and scale"""
	tx, ty = e, f

	if abs(b*c) < error:
		cosa, sina = 1., 0.
		sx, hy = a, b
		hx, sy = c, d
	else:
		sign = 1. if a*d>=b*c else -1.
		cosa, sina = a+sign*d, b-sign*c
		h = hypot(cosa, sina)
		cosa, sina = cosa/h, sina/h
		sx, hy = a*cosa + b*sina, b*cosa - a*sina
		hx, sy = c*cosa + d*sina, d*cosa - c*sina
		sx -= hx*hy/sy
	return (tx, ty), (cosa, sina), (hx, hy), (sx, sy)


def _list_from_params(t, r, sk, s, error=1e-6):
	(tx, ty), (cosa, sina), (hx, hy), (sx, sy) = t, r, sk, s
	transforms = []
	if (tx, ty) != (0., 0.):
		transforms.append(Translate(tx, ty))
	if abs(sina) > abs(cosa)*error:
		transforms.append(Rotate(degrees(atan2(sina, cosa))))
	if abs(hx) > abs(sy)*error:
		transforms.append(SkewX(degrees(atan2(hx, sy))))
	if abs(hy) > abs(sx)*error:
		transforms.append(SkewY(degrees(atan2(hy, sx))))
	if any(abs(1.-s) > error for s in (sx, sy)):
		transforms.append(Scale(sx, sy))
	return transforms


def _list_from_matrix(a, b, c, d, e, f, error=1e-6):
	return _list_from_params(*_params_from_matrix(a, b, c, d, e, f, error),
	                         error=error)


class TransformList(list, _Transform):
	@classmethod
	def from_matrix(Cls, a=1., b=0., c=0., d=1., e=0., f=0.):
		return Cls(_list_from_matrix(a, b, c, d, e, f))
	
	@classmethod
	def from_params(Cls, t=(0., 0.), r=(1., 0.), sk=(0., 0.), s=(1., 1.)):
		return Cls(_list_from_params(t, r, sk, s))
	
	def matrix(self):
		ox, oy = self.unproject(0, 0)
		xx, xy = self.unproject(1, 0)
		yx, yy = self.unproject(0, 1)
		a, b, c, d, e, f = xx-ox, xy-oy, yx-ox, yy-oy, ox, oy
		return a, b, c, d, e, f
	
	def params(self):
		return _params_from_matrix(*self.matrix())
	
	def render(self):
		for transform in self:
			transform.render()
	
	def unproject(self, x=0, y=0):
		for transform in reversed(self):
			x, y = transform.unproject(x, y)
		return x, y

	def project(self, x=0, y=0):
		for transform in self:
			x, y = transform.project(x, y)
		return x, y
	
	def inverted(self):
		return TransformList(t.inverted() for t in reversed(self))
	
	def normalized(self):
		return self.from_matrix(*self.matrix())

	def __add__(self, l):
		return TransformList(list(self) + l)
