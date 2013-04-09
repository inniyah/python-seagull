# -*- coding: utf-8 -*-

"""
OpenGL utilities
"""

# imports ####################################################################

from math import floor, ceil
from ctypes import c_float, c_int

try:
	from . import opengles as _gl
except:
	from . import opengl as _gl


# helpers ####################################################################

def gl_preparer(clear_color=(1., 1., 1., 0.)):
	def prepare(clear_color=clear_color):
		_gl.EnableClientState(_gl.VERTEX_ARRAY)
		_gl.Enable(_gl.BLEND)
		_gl.BlendFunc(_gl.SRC_ALPHA, _gl.ONE_MINUS_SRC_ALPHA)
		_gl.ClearColor(*clear_color)
		_gl.Enable(_gl.STENCIL_TEST)
		_gl.Enable(_gl.TEXTURE_2D)
	return prepare

gl_prepare = gl_preparer()


def gl_reshaper(depth=1, centered=False):
	def reshape(width, height, depth=depth, centered=centered):
		_gl.Viewport(0, 0, width, height)
		
		_gl.MatrixMode(_gl.PROJECTION)
		_gl.LoadIdentity()
		_gl.Ortho(0, width, height, 0, -depth, depth)
		if centered:
			_gl.Translate(width/2, height/2, 0)
	
		_gl.MatrixMode(_gl.MODELVIEW)
		_gl.LoadIdentity()
		_gl.Clear(_gl.COLOR_BUFFER_BIT|_gl.STENCIL_BUFFER_BIT)
	return reshape

gl_reshape = gl_reshaper()


def gl_displayer(*_elements):
	def display(*elements):
		_gl.Clear(_gl.COLOR_BUFFER_BIT)
		for elem in elements or _elements:
			elem.render()
		_gl.Flush()
	return display

gl_display = gl_displayer()


# textures ###################################################################

def create_texture(width, height, data=None, format=_gl.RGBA, max_level=0,
                   min_filter=_gl.LINEAR_MIPMAP_LINEAR, internalformat=None):
	if isinstance(format, str):
		format = {
			"RGB":  _gl.RGB,
			"RGBA": _gl.RGBA,
			"LA":   _gl.LUMINANCE_ALPHA,
			"L":    _gl.ALPHA,
		}[format]
	
	_gl.PixelStorei(_gl.UNPACK_ALIGNMENT, 1)

	texture_id = _gl.GenTextures(1)
	_gl.BindTexture(_gl.TEXTURE_2D, texture_id)
	
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_BASE_LEVEL, 0)
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_MAX_LEVEL, max_level)
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_MIN_FILTER, min_filter)
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_MAG_FILTER, _gl.LINEAR)
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_WRAP_R, _gl.CLAMP_TO_EDGE)
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_WRAP_S, _gl.CLAMP_TO_EDGE)
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_WRAP_T, _gl.CLAMP_TO_EDGE)

	_gl.TexImage2D(_gl.TEXTURE_2D, 0, internalformat or format,
	               width, height, 0,
	               format, _gl.UNSIGNED_BYTE, data)
	_gl.GenerateMipmap(_gl.TEXTURE_2D)
	
	return texture_id

class OffscreenContext(object):
	"""offscreen framebuffer context."""
	fbos = []
	origins = []
	
	def __init__(self, aabbox, bg_color=None):
		self.samples = _gl.GetInteger(_gl.SAMPLES)
		self.aabbox = aabbox
		self.bg_color = bg_color
	
	def __enter__(self):
		(x_min, y_min), (x_max, y_max) = self.aabbox
		if x_max <= x_min or y_max <= y_min:
			return (0, 0), (0, 0), 0
		
		try:
			self.fb_background, _, _ = self.fbos[-1]
			X_min, Y_min, X_max, Y_max = self.origins[-1]
		except IndexError:
			self.fb_background = 0
			X, Y, W, H = _gl.GetInteger(_gl.VIEWPORT)
			X_min, Y_min, X_max, Y_max = X, Y, X+W, Y+H

		x_min, x_max = max(int(floor(x_min-1)), X_min), min(int(ceil(x_max+1)), X_max)
		y_min, y_max = max(int(floor(y_min-1)), Y_min), min(int(ceil(y_max+1)), Y_max)
	
		width, height = x_max-x_min, y_max-y_min
		if width <= 0 or height <= 0:
			return (0, 0), (0, 0), 0

		# fbo with multisample render buffer
		fb_ms = _gl.GenFramebuffers(1)
		_gl.BindFramebuffer(_gl.DRAW_FRAMEBUFFER, fb_ms)
		rb_color, rb_depth_stencil = _gl.GenRenderbuffers(2)
		_gl.BindRenderbuffer(_gl.RENDERBUFFER, rb_color)
		_gl.RenderbufferStorageMultisample(_gl.RENDERBUFFER, self.samples, _gl.RGBA, width, height)
		_gl.FramebufferRenderbuffer(_gl.FRAMEBUFFER, _gl.COLOR_ATTACHMENT0, _gl.RENDERBUFFER, rb_color)
		_gl.BindRenderbuffer(_gl.RENDERBUFFER, rb_depth_stencil)
		_gl.RenderbufferStorageMultisample(_gl.RENDERBUFFER, self.samples, _gl.DEPTH_STENCIL, width, height)
		_gl.FramebufferRenderbuffer(_gl.FRAMEBUFFER, _gl.DEPTH_STENCIL_ATTACHMENT, _gl.RENDERBUFFER, rb_depth_stencil)
	
		assert _gl.CheckFramebufferStatus(_gl.FRAMEBUFFER) == _gl.FRAMEBUFFER_COMPLETE
	
		# offscreen rendering
		_gl.BindFramebuffer(_gl.READ_FRAMEBUFFER, self.fb_background)
		if self.bg_color is None:
			x, y = x_min-X_min, Y_max-y_max
			_gl.BlitFramebuffer(x, y, x+width, y+height,
			                    0, 0, width, height,
			                    _gl.COLOR_BUFFER_BIT|_gl.STENCIL_BUFFER_BIT,
			                    _gl.NEAREST)
		else:
			_gl.PushAttrib(_gl.COLOR_BUFFER_BIT)
			_gl.ClearColor(*self.bg_color)
			_gl.Clear(_gl.COLOR_BUFFER_BIT|_gl.STENCIL_BUFFER_BIT)
			_gl.PopAttrib(_gl.COLOR_BUFFER_BIT)

		_gl.PushAttrib(_gl.VIEWPORT_BIT)
		_gl.Viewport(0, 0, width, height)
	
		_gl.MatrixMode(_gl.PROJECTION)
		_gl.PushMatrix()
		_gl.LoadIdentity()
		_gl.Ortho(x_min, x_max, y_max, y_min, -1, 1)
		_gl.MatrixMode(_gl.MODELVIEW)
	
		self.fbos.append((fb_ms, rb_color, rb_depth_stencil))
		self.origins.append((x_min, y_min, x_max, y_max))

		self.texture_color = _gl.GenTextures(1)
		return (x_min, y_min), (width, height), self.texture_color
		
	def __exit__(self, *args):
		try:
			self.texture_color
		except AttributeError:
			return
		
		fb_ms, rb_color, rb_depth_stencil = self.fbos.pop()
		x_min, y_min, x_max, y_max = self.origins.pop()
		width, height = x_max-x_min, y_max-y_min

		_gl.MatrixMode(_gl.PROJECTION)
		_gl.PopMatrix()
		_gl.MatrixMode(_gl.MODELVIEW)

		_gl.PopAttrib(_gl.VIEWPORT_BIT)

		# fbo for texture
		fb_texture = _gl.GenFramebuffers(1)
		_gl.BindFramebuffer(_gl.DRAW_FRAMEBUFFER, fb_texture)
		_gl.BindTexture(_gl.TEXTURE_2D, self.texture_color)
		format = _gl.RGB if self.bg_color is None else _gl.RGBA
		_gl.TexImage2D(_gl.TEXTURE_2D, 0,
		               format, width, height, 0,
		               format, _gl.UNSIGNED_BYTE, None)
		_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_WRAP_R, _gl.CLAMP_TO_EDGE)
		_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_WRAP_S, _gl.CLAMP_TO_EDGE)
		_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_WRAP_T, _gl.CLAMP_TO_EDGE)
		_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_MAG_FILTER, _gl.NEAREST)
		_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_MIN_FILTER, _gl.NEAREST)
		_gl.FramebufferTexture2D(_gl.FRAMEBUFFER, _gl.COLOR_ATTACHMENT0,
		                         _gl.TEXTURE_2D, self.texture_color, 0)
		assert _gl.CheckFramebufferStatus(_gl.FRAMEBUFFER) == _gl.FRAMEBUFFER_COMPLETE

		# blit render buffer to texture
		_gl.BindFramebuffer(_gl.READ_FRAMEBUFFER, fb_ms)
		_gl.BlitFramebuffer(0, 0, width, height, 0, height, width, 0,
		                    _gl.COLOR_BUFFER_BIT, _gl.NEAREST)
		
		# clean up
		_gl.DeleteRenderbuffers(2, [rb_color, rb_depth_stencil])
		_gl.DeleteFramebuffers(2, [fb_ms, fb_texture])

		_gl.BindFramebuffer(_gl.DRAW_FRAMEBUFFER, self.fb_background)


# shaders ####################################################################

def create_shader(shader_type, source):
	"""compile a shader."""
	shader = _gl.CreateShader(shader_type)
	_gl.ShaderSource(shader, source)
	_gl.CompileShader(shader)
	if _gl.GetShaderiv(shader, _gl.COMPILE_STATUS) != _gl.TRUE:
		raise RuntimeError(_gl.GetShaderInfoLog(shader))
	return shader

def create_program(*shaders):
	program = _gl.CreateProgram()
	for shader in shaders:
		_gl.AttachShader(program, shader)
	_gl.LinkProgram(program)
	if _gl.GetProgramiv(program, _gl.LINK_STATUS) != _gl.TRUE:
		raise RuntimeError(_gl.GetProgramInfoLog(program))
	return program

_locations = {}
def location(program, uniform):
	global _locations
	try:
		locations = _locations[program]
	except KeyError:
		locations = _locations[program] = dict()
	try:
		location = locations[uniform]
	except KeyError:
		location = locations[uniform] = _gl.GetUniformLocation(program, uniform.encode())
	return location


_c_types = {
	float: c_float,
	int:   c_int,
	bool:  c_int,
}

_Uniforms = {
	(1, c_float): _gl.Uniform1fv,
	(2, c_float): _gl.Uniform2fv,
	(4, c_float): _gl.Uniform4fv,
	(1, c_int):   _gl.Uniform1iv,
}

def set_uniform(program, uniform, values):
	v0, n = values[0], len(values)
	if isinstance(v0, tuple):
		l, t = len(v0), _c_types[type(v0[0])]
		values = (t * (l*n))(*[u for value in values for u in value])
	else:
		l, t = 1, _c_types[type(v0)]
		values = (t * n)(*values)
	_Uniforms[l, t](location(program, uniform), n, values)
