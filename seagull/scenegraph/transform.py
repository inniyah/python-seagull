# -*- coding: utf-8 -*-

"""
transforms
"""

# imports ####################################################################

from math import radians, cos, sin, hypot, degrees, atan2, tan

from ._common import _Base


# transforms #################################################################

class _Transform(_Base):
	_state_attributes = ["tag"]
	attributes = []
	
	def project(self, x=0, y=0):
		a, b, c, d, e, f = self.abcdef
		return a*x+c*y+e, b*x+d*y+f
	
	def __mul__(self, other):
		sa, sb, sc, sd, se, sf = self.abcdef
		oa, ob, oc, od, oe, of = other.abcdef
		a, c, e = sa*oa+sc*ob, sa*oc+sc*od, sa*oe+sc*of+se
		b, d, f = sb*oa+sd*ob, sb*oc+sd*od, sb*oe+sd*of+sf
		return Matrix(a, b, c, d, e, f)
	
	def params(self, error=1e-6):
		"""separate translation, rotation, shear and scale"""
		a, b, c, d, e, f = self.abcdef
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

	def uniform(self):
		a, b, c, d, e, f = self.abcdef
		return [(a, b, 0., c, d, 0., e, f, 1.)]

	def __str__(self):
		return "%s(" % self.tag + \
		       ",".join(str(getattr(self, a)) for a in self.attributes) + \
		       ")"


class Translate(_Transform):
	tag = "translate"
	attributes = ["tx", "ty"]
	_state_attributes = _Transform._state_attributes + attributes
	
	def __init__(self, tx=0, ty=0):
		self.tx, self.ty = tx, ty

	def inverse(self):
		return Translate(-self.tx, -self.ty)
	
	@property
	def abcdef(self):
		return 1., 0., 0., 1., self.tx, self.ty


class Scale(_Transform):
	tag = "scale"
	attributes = ["sx", "sy"]
	_state_attributes = _Transform._state_attributes + attributes
	
	def __init__(self, sx=1., sy=None):
		self.sx = sx
		self.sy = sy or sx
	
	def inverse(self):
		return Scale(1./self.sx, 1./self.sy)
	
	@property
	def abcdef(self):
		return self.sx, 0., 0., self.sy, 0., 0.

	
class Rotate(_Transform):
	tag = "rotate"
	attributes = ["a", "cx", "cy"]
	_state_attributes = _Transform._state_attributes + attributes
	
	def __init__(self, a=0, cx=0, cy=0):
		self.a = a
		self.cx, self.cy = cx, cy

	def inverse(self):
		return Rotate(-self.a, self.cx, self.cy)
	
	@property
	def abcdef(self):
		a, cx, cy = radians(self.a), self.cx, self.cy
		c, s = cos(a), sin(a)
		return c, s, -s, c, cx*(1.-c)+cy*s, cy*(1.-c)-cx*s


class SkewX(_Transform):
	tag = "skewX"
	attributes = ["ax"]
	_state_attributes = _Transform._state_attributes + attributes
	
	def __init__(self, ax=0.):
		self.ax = ax

	def inverse(self):
		return SkewX(-self.ax)
	
	@property
	def abcdef(self):
		t = tan(radians(self.ax))
		return 1., 0., t, 1., 0., 0.


class SkewY(_Transform):
	tag = "skewY"
	attributes = ["ay"]
	_state_attributes = _Transform._state_attributes + attributes
	
	def __init__(self, ay=0.):
		self.ay = ay

	def inverse(self):
		return SkewY(-self.ay)
	
	@property
	def abcdef(self):
		t = tan(radians(self.ay))
		return 1., t, 0., 1., 0., 0.


class Matrix(_Transform):
	tag = "matrix"
	attributes = ["a", "b", "c", "d", "e", "f"]
	_state_attributes = _Transform._state_attributes + attributes
	
	def __init__(self, a=1., b=0., c=0., d=1., e=0., f=0.):
		self.a, self.c, self.e = a, c, e
		self.b, self.d, self.f = b, d, f
	
	def get_abcdef(self):
		return self.a, self.b, self.c, self.d, self.e, self.f
	def set_abcdef(self, abcdef):
		self.a, self.b, self.c, self.d, self.e, self.f = abcdef
	abcdef = property(get_abcdef, set_abcdef)
	
	def inverse(self):
		a, b, c, d, e, f = self.abcdef
		det = a*d-b*c
		return Matrix(*(u/det for u in (d, -b, -c, a, c*f-e*d, b*e-a*f)))


def Ortho(left, right, bottom, top):
	width, height = right-left, top-bottom
	a, c, e = 2./width, 0.,        -(left+right)/width
	b, d, f = 0.,       2./height, -(bottom+top)/height
	return Matrix(a, b, c, d, e, f)


def Stretch(x, y, width, height):
	a, c, e = width, 0.,     x
	b, d, f = 0.,    height, y
	return Matrix(a, b, c, d, e, f)

def Shrink(x, y, width, height):
	a, c, e = 1./width, 0.,        -x/width
	b, d, f = 0.,       1./height, -y/height
	return Matrix(a, b, c, d, e, f)


# helpers ####################################################################

def product(p=Matrix(), *qs):
	for q in qs:
		p = p * q
	return p

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

def normalized(transform):
	return _list_from_params(*product(*transform).params())
