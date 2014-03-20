# -*- coding: utf-8 -*-

"""
OpenGL utilities
"""

# imports ####################################################################

from struct import pack
from math import floor, ceil

from . import gl as _gl


# helpers ####################################################################

def gl_preparer(clear_color=(1., 1., 1., 0.)):
	def prepare(clear_color=clear_color):
		_gl.Enable(_gl.BLEND)
		_gl.BlendFunc(_gl.SRC_ALPHA, _gl.ONE_MINUS_SRC_ALPHA)
		_gl.ClearColor(*clear_color)
		_gl.Enable(_gl.STENCIL_TEST)
		
		version = get_opengl_version()
		if version < (3, 2):
			_gl.Enable(_gl.TEXTURE_2D)
		if version >= (3, 2):
			_gl.BindVertexArray(_gl.GenVertexArrays(1))
		if version >= (4, 0):
			_gl.MinSampleShading(1.)
	return prepare

gl_prepare = gl_preparer()


def gl_reshape(width, height):
	_gl.Viewport(0, 0, width, height)


def gl_displayer(*_elements, swap_buffers=None):
	def display(*elements, swap_buffers=swap_buffers):
		_gl.Clear(_gl.COLOR_BUFFER_BIT|_gl.STENCIL_BUFFER_BIT)
		for elem in elements or _elements:
			elem.render()
		_gl.Flush()
		if swap_buffers is not None:
			swap_buffers()
	return display

gl_display = gl_displayer()


# textures ###################################################################

class _texture_id(int):
	def __del__(self):
		try:
			_gl.DeleteTextures((_gl.uint*1)(self))
		except AttributeError:
			pass

def create_texture(width, height, data=None, format=_gl.RGBA, max_level=0,
                   min_filter=_gl.LINEAR_MIPMAP_LINEAR,
                   mag_filter=_gl.LINEAR,
                   internalformat=None):
	if isinstance(format, str):
		format = {
			"RGB":  _gl.RGB,
			"RGBA": _gl.RGBA,
		}[format]
	
	_gl.PixelStorei(_gl.UNPACK_ALIGNMENT, 1)

	texture_id = _texture_id(_gl.GenTextures(1))
	_gl.BindTexture(_gl.TEXTURE_2D, texture_id)
	
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_BASE_LEVEL, 0)
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_MAX_LEVEL, max_level)
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_MIN_FILTER, min_filter)
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_MAG_FILTER, mag_filter)
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_WRAP_R, _gl.CLAMP_TO_EDGE)
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_WRAP_S, _gl.CLAMP_TO_EDGE)
	_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_WRAP_T, _gl.CLAMP_TO_EDGE)

	_gl.TexImage2D(_gl.TEXTURE_2D, 0, internalformat or format,
	               width, height, 0,
	               format, _gl.UNSIGNED_BYTE, data)
	_gl.GenerateMipmap(_gl.TEXTURE_2D)
	
	return texture_id


class OffscreenContext:
	"""offscreen framebuffer context."""
	
	def __init__(self):
		self.fbos = [(0, None, None)]
		_, _, width, height = _gl.GetIntegerv(_gl.VIEWPORT)
		self.orthos = [(0, int(width), int(height), 0)]
		self.colors = []
		self.textures = []
	
	def __call__(self, aabbox, bg_color=None):
		self.samples = _gl.GetInteger(_gl.SAMPLES)
		self.aabbox = aabbox
		self.bg_color = bg_color
		return self
	
	def __enter__(self):
		self.textures.append(0)

		(x_min, y_min), (x_max, y_max) = self.aabbox
		if x_max <= x_min or y_max <= y_min:
			return (0, 0), (0, 0), 0
		
		fb_background, _, _ = self.fbos[-1]
		X_min, X_max, Y_max, Y_min = self.orthos[-1]

		x_min, x_max = max(int(floor(x_min-1)), X_min), min(int(ceil(x_max+1)), X_max)
		y_min, y_max = max(int(floor(y_min-1)), Y_min), min(int(ceil(y_max+1)), Y_max)
	
		width, height = x_max-x_min, y_max-y_min
		if width <= 0 or height <= 0:
			return (0, 0), (0, 0), 0

		_gl.Viewport(0, 0, width, height)

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
		if self.bg_color is None:
			_gl.BindFramebuffer(_gl.READ_FRAMEBUFFER, fb_background)
			x, y = x_min-X_min, Y_max-y_max
			_gl.BlitFramebuffer(x, y, x+width, y+height,
			                    0, 0, width, height,
			                    _gl.COLOR_BUFFER_BIT|_gl.STENCIL_BUFFER_BIT,
			                    _gl.NEAREST)
		else:
			_clear_color = _gl.GetFloat(_gl.COLOR_CLEAR_VALUE)
			_gl.ClearColor(*self.bg_color)
			_gl.Clear(_gl.COLOR_BUFFER_BIT|_gl.STENCIL_BUFFER_BIT)
			_gl.ClearColor(*_clear_color)

		self.fbos.append((fb_ms, rb_color, rb_depth_stencil))
		self.orthos.append((x_min, x_max, y_max, y_min))
		self.colors.append(self.bg_color)
		
		self.textures[-1] = texture_color = _texture_id(_gl.GenTextures(1))
		return (x_min, y_min), (width, height), texture_color
	
	
	def __exit__(self, *args):
		texture_color = self.textures.pop()
		if not texture_color:
			return
		
		fb_ms, rb_color, rb_depth_stencil = self.fbos.pop()
		x_min, x_max, y_max, y_min = self.orthos.pop()
		width, height = x_max-x_min, y_max-y_min
		bg_color = self.colors.pop()

		# fbo for texture
		fb_texture = _gl.GenFramebuffers(1)
		_gl.BindFramebuffer(_gl.DRAW_FRAMEBUFFER, fb_texture)
		_gl.BindTexture(_gl.TEXTURE_2D, texture_color)
		format = _gl.RGB if bg_color is None else _gl.RGBA
		_gl.TexImage2D(_gl.TEXTURE_2D, 0,
		               format, width, height, 0,
		               format, _gl.UNSIGNED_BYTE, None)
		_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_WRAP_R, _gl.CLAMP_TO_EDGE)
		_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_WRAP_S, _gl.CLAMP_TO_EDGE)
		_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_WRAP_T, _gl.CLAMP_TO_EDGE)
		_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_MAG_FILTER, _gl.NEAREST)
		_gl.TexParameteri(_gl.TEXTURE_2D, _gl.TEXTURE_MIN_FILTER, _gl.NEAREST)
		_gl.FramebufferTexture2D(_gl.FRAMEBUFFER, _gl.COLOR_ATTACHMENT0,
		                         _gl.TEXTURE_2D, texture_color, 0)
		assert _gl.CheckFramebufferStatus(_gl.FRAMEBUFFER) == _gl.FRAMEBUFFER_COMPLETE

		# blit render buffer to texture
		_gl.BindFramebuffer(_gl.READ_FRAMEBUFFER, fb_ms)
		_gl.BlitFramebuffer(0, 0, width, height, 0, height, width, 0,
		                    _gl.COLOR_BUFFER_BIT, _gl.NEAREST)
		
		# clean up
		_gl.DeleteRenderbuffers(2, (_gl.uint * 2)(rb_color, rb_depth_stencil))
		_gl.DeleteFramebuffers(2, (_gl.uint * 2)(fb_ms, fb_texture))
		
		fb_background, _, _ = self.fbos[-1]
		_gl.BindFramebuffer(_gl.DRAW_FRAMEBUFFER, fb_background)

		x_min, x_max, y_max, y_min = self.orthos[-1]
		_gl.Viewport(0, 0, x_max-x_min, y_max-y_min)


# vertex buffer objects ######################################################

def _c_array(points):
	"""turn list of 2-tuple into c array of floats."""
	n = len(points)
	try:
		s = len(points[0])
	except:
		return n, pack("%df" % n, *points)
	return n, pack("%df" % (s*n), *(u for point in points for u in point))

class _vbo_id(int):
	"""auto releasing vbo id"""
	def __del__(self):
		try:
			_gl.DeleteBuffers(1, (_gl.uint*1)(self))
		except AttributeError:
			pass

def create_vbo(points):
	n, vertices = _c_array(points)
	vbo_id = _vbo_id(_gl.GenBuffers(1))
	_gl.BindBuffer(_gl.ARRAY_BUFFER, vbo_id)
	_gl.BufferData(_gl.ARRAY_BUFFER, vertices, _gl.STATIC_DRAW)
	return n, vbo_id


# shaders ####################################################################

def get_opengl_version():
	"""return opengl version."""
	version = _gl.GetString(_gl.VERSION).decode()
	version = version.split()[0]
	version = map(int, version.split("."))
	return tuple(version)

def create_shader(shader_type, source, **kwargs):
	"""compile a shader."""
	version = get_opengl_version()
	if version < (2, 1):
		raise RuntimeError("unsupported OpenGL version %s", version)
	defines = {"GLSL_VERSION": "120" if version < (3, 2) else "150"}
	defines.update(kwargs)
	shader = _gl.CreateShader(shader_type)
	_gl.ShaderSource(shader, source % defines)
	_gl.CompileShader(shader)
	if _gl.GetShaderiv(shader, _gl.COMPILE_STATUS) != _gl.TRUE:
		raise RuntimeError(_gl.GetShaderInfoLog(shader))
	return shader

def create_program(*shaders, attrib_locations={}):
	program = _gl.CreateProgram()
	for shader in shaders:
		_gl.AttachShader(program, shader)
	for attrib in attrib_locations:
		_gl.BindAttribLocation(program, attrib_locations[attrib], attrib)
		_gl.EnableVertexAttribArray(attrib_locations[attrib])
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
	float: _gl.float,
	int:   _gl.int,
	bool:  _gl.int,
}

_Uniforms = {
	(1, _gl.float): _gl.Uniform1fv,
	(2, _gl.float): _gl.Uniform2fv,
	(3, _gl.float): _gl.Uniform3fv,
	(4, _gl.float): _gl.Uniform4fv,
	(9, _gl.float): lambda location, n, values: \
	                	_gl.UniformMatrix3fv(location, n, _gl.FALSE, values),
	(1, _gl.int):   _gl.Uniform1iv,
}

def set_uniform(program, uniform, values):
	v0, n = values[0], len(values)
	if isinstance(v0, tuple):
		l, t = len(v0), _c_types[type(v0[0])]
		values = (t * (l*n))(*(u for value in values for u in value))
	else:
		l, t = 1, _c_types[type(v0)]
		values = (t * n)(*values)
	_Uniforms[l, t](location(program, uniform), n, values)
