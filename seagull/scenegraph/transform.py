# -*- coding: utf-8 -*-

"""
transforms
"""

# imports ####################################################################

from math import radians, cos, sin, sqrt, hypot, degrees, atan2, tan

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
	def __init__(self, X=0, Y=0, Z=0):
		self.O = X, Y, Z
		
	def render(self):
		_gl.LoadIdentity()
		_gl.Translate(*self.O)


def _translate(x, y, z, tx=0, ty=0, tz=0):
	return x+tx, y+ty, z+tz

def _scale(x, y, z, sx=1., sy=1., sz=1.):
	return x*sx, y*sy, z*sz
	
def _rotate(x, y, z, a=0., nx=0., ny=0., nz=1.):
	a = radians(a)
	c, s = cos(a), sin(a)
	h = sqrt(nx*nx + ny*ny + nz*nz)
	nx, ny, nz = nx/h, ny/h, nz/h
	sx, sy, sz = s*nx, s*ny, s*nz
	oc = 1.-c
	return (x*(oc*nx*nx+c)  + y*(oc*nx*ny-sz) + z*(oc*nx*nz+sy),
	        x*(oc*nx*ny+sz) + y*(oc*ny*ny+c)  + z*(oc*ny*nz-sx),
	        x*(oc*nx*nz-sy) + y*(oc*ny*nz+sx) + z*(oc*nz*nz+c))

def _shearx(x, y, z, ax=0.):
	t = tan(radians(ax))
	return x + t*y, y, z

def _sheary(x, y, z, ay=0.):
	t = tan(radians(ay))
	return x, y + t*x, z


class Translate(_Transform):
	_state_attributes = _Transform._state_attributes + [
		"tx", "ty", "tz",
	]
	
	def __init__(self, tx=0, ty=0, tz=0):
		self.tx, self.ty, self.tz = tx, ty, tz

	def render(self):
		_gl.Translate(self.tx, self.ty, self.tz)
	
	def unproject(self, x=0, y=0, z=0):	
		x, y, z = _translate(x, y, z, self.tx, self.ty, self.tz)
		return x, y, z

	def project(self, x=0, y=0, z=0):
		x, y, z = _translate(x, y, z, -self.tx, -self.ty, -self.tz)
		return x, y, z
		
	def __str__(self):
		return "translate(" + \
		       ",".join(str(t) for t in [self.tx, self.ty]) + \
		       ")"


class Scale(_Transform):
	_state_attributes = _Transform._state_attributes + [
		"sx", "sy", "sz",
	]
	
	def __init__(self, sx=1., sy=None, sz=None):
		self.sx = sx
		self.sy = sy or sx
		self.sz = sz or sx
		
	def render(self):
		_gl.Scale(self.sx, self.sy, self.sz)
		
	def unproject(self, x=0, y=0, z=0):
		x, y, z = _scale(x, y, z, self.sx, self.sy, self.sz)
		return x, y, z

	def project(self, x=0, y=0, z=0):
		x, y, z = _scale(x, y, z, 1./self.sx, 1./self.sy, 1./self.sz)
		return x, y, z

	def __str__(self):
		return "scale(" + \
		       ",".join(str(t) for t in [self.sx, self.sy]) + \
		       ")"

	
class Rotate(_Transform):
	_state_attributes = _Transform._state_attributes + [
		"a",
		"cx", "cy", "cz",
		"nx", "ny", "nz",
	]
	
	def __init__(self, a=0, cx=0, cy=0, cz=0, nx=0, ny=0, nz=1):
		self.a = a
		self.cx, self.cy, self.cz = cx, cy, cz
		self.nx, self.ny, self.nz = nx, ny, nz
		
	def render(self):
		_gl.Translate(self.cx, self.cy, self.cz)
		_gl.Rotate(self.a, self.nx, self.ny, self.nz)
		_gl.Translate(-self.cx, -self.cy, -self.cz)
		
	def unproject(self, x=0, y=0, z=0):
		x, y, z = _translate(x, y, z, -self.cx, -self.cy, -self.cz)
		x, y, z = _rotate(x, y, z, self.a, self.nx, self.ny, self.nz)
		x, y, z = _translate(x, y, z, self.cx, self.cy, self.cz)
		return x, y, z

	def project(self, x=0, y=0, z=0):
		x, y, z = _translate(x, y, z, -self.cx, -self.cy, -self.cz)
		x, y, z = _rotate(x, y, z, -self.a, self.nx, self.ny, self.nz)
		x, y, z = _translate(x, y, z, self.cx, self.cy, self.cz)
		return x, y, z

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

	def unproject(self, x=0, y=0, z=0):
		x, y, z = _shearx(x, y, z, self.ax)
		return x, y, z
	
	def project(self, x=0, y=0, z=0):
		x, y, z = _shearx(x, y, z, -self.ax)
		return x, y, z

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

	def unproject(self, x=0, y=0, z=0):
		x, y, z = _sheary(x, y, z, self.ay)
		return x, y, z
	
	def project(self, x=0, y=0, z=0):
		x, y, z = _sheary(x, y, z, -self.ay)
		return x, y, z

	def __str__(self):
		return "skewY(%s)" % self.ay


class TransformList(list, _Transform):
	def render(self):
		for transform in self:
			transform.render()

	def unproject(self, x=0, y=0, z=0):
		for transform in reversed(self):
			x, y, z = transform.unproject(x, y, z)
		return x, y, z

	def project(self, x=0, y=0, z=0):
		for transform in self:
			x, y, z = transform.project(x, y, z)
		return x, y, z
	
	def normalized(self):
		ox, oy, _ = self.unproject(0, 0, 0)
		xx, xy, _ = self.unproject(1, 0, 0)
		
		dx, dy = xx-ox, xy-oy
		a = degrees(atan2(dy, dx))
		s = hypot(dx, dy)
		
		return TransformList([Translate(ox, oy), Rotate(a), Scale(s)])

	def __add__(self, l):
		return TransformList(list(self) + l)
