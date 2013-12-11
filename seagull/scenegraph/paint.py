# -*- coding: utf-8 -*-

"""
paint servers
"""


# imports ####################################################################

from ..opengl import gl as _gl
from ..opengl.utils import (create_shader, create_program, set_uniform)
from ._common import _Element, _Context

from .transform import TransformList, Translate, Scale


# shaders ####################################################################

_VERT_SHADER = """
	void main() {
		gl_ClipVertex = gl_ModelViewMatrix * gl_Vertex;
		gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
		gl_TexCoord[0] = gl_TextureMatrixInverse[0] * gl_Vertex;
		gl_TexCoord[1] = gl_TextureMatrixInverse[1] * gl_ClipVertex;
		gl_FrontColor = gl_Color;
	}
"""

_MAIN_FRAG_SHADER = """
	uniform bool masking;
	uniform sampler2D mask;
	
	const vec4 luminance = vec4(.2125, .7154, .0721, 0.);
	
	vec4 color(); // filling color
	
	void main() {
		vec4 color = color();
		if(masking) {
			color.a *= dot(luminance, texture2D(mask, gl_TexCoord[1].xy));
		}
		gl_FragColor = gl_Color * color;
	}
"""


# filling fragment shaders ###################################################

_SOLID_FRAG_SHADER = """
	vec4 color() {
		return vec4(1., 1., 1., 1.);
	}

"""

_TEXTURE_FRAG_SHADER = """
	uniform sampler2D texture;
	
	vec4 color() {
		return texture2D(texture, gl_TexCoord[0].xy);
	}

"""

MAX_STOPS = 21

_GRADIENT_FRAG_SHADER = """
	const int N = %(MAX_STOPS)s;
	
	uniform int n;
	uniform float os[N];
	uniform vec4 colors[N];
	uniform int spread;
	
	float o(vec2 p); // offset at point p in the gradient
	
	float spread(float o) {
		// offset according to spread method
		float pad = o;
		float repeat = fract(o);
		float reflect = mod(o, 2.);
		if(reflect > 1.)
			reflect = 2.-reflect;
		return vec3(pad, reflect, repeat)[spread];
	}
	
	vec4 gradient(float o) {
		// color at offset o in the gradient
		float oa, oi = os[0];
		vec4 ca, ci = colors[0];
		for(int i = 0; i < n; i++) {
			oa = os[i]; ca = colors[i];
			if(o <= oa) break;
			oi = oa; ci = ca;
		}
		float ki = (oi == oa) ? 1. : (oa-o)/(oa-oi);
		return ki*ci + (1.-ki)*ca;
	}
	
	vec4 igradient(float ob, float oe) {
		// color integrated between offsets ob and oe
		// (useful for antialiasing when distance between stops is subpixel)
		vec4 c = gradient(ob);
		vec4 ic = vec4(0.);
		float lo = oe-ob;

		for(int i = 0; i < n; i++) {
			float o = os[i];
			if(o <= ob) continue;
			if(o > oe) break;
			
			ic += (o-ob)*c;
			c = colors[i];
			ic += (o-ob)*c;
			ob = o;
		}
		ic += (oe-ob)*c;
		c = gradient(oe);
		ic += (oe-ob)*c;
		return ic/lo/2.;
	}
	
	vec4 color() {
		vec2 p = gl_TexCoord[0].xy;
		float o = o(p);
		float s = spread(o);

//		vec4 color = gradient(s);
		float how = length(vec2(dFdx(o), dFdy(o)))/2.;
		vec4 color = igradient(s-how, s+how);
		
		return color;
	}
""" % {"MAX_STOPS": MAX_STOPS}

_LINEAR_OFFSET_FRAG_SHADER = """
	uniform vec2 p1;
	uniform vec2 p2;

	float o(vec2 p) {
		// offset at point p in the linear gradient
		vec2 u = p - p1;
		vec2 v = p2 - p1;
		return dot(u, v)/dot(v, v);
	}
"""

_RADIAL_OFFSET_FRAG_SHADER = """
	uniform vec2 c;
	uniform float r;
	uniform vec2 f;

	float o(vec2 p) {
		// offset at point p in the radial gradient
		vec2 u = p - f;
		vec2 v = c - f;
		float a2 = dot(v, v) - r*r;
		float a1 = dot(u, v);
		float a0 = dot(u, u);
		if(a2 == 0.) {
			return .5*a0/a1; // at first order sqrt(1+x) == 1+x/2
		} else {
			return (a1-sqrt(a1*a1-a2*a0))/a2;
		}
	}
"""

_shaders = {
	"solid_color": [
		(_gl.VERTEX_SHADER,   _VERT_SHADER),
		(_gl.FRAGMENT_SHADER, _SOLID_FRAG_SHADER),
		(_gl.FRAGMENT_SHADER, _MAIN_FRAG_SHADER),
	],
	"texture": [
		(_gl.VERTEX_SHADER,   _VERT_SHADER),
		(_gl.FRAGMENT_SHADER, _TEXTURE_FRAG_SHADER),
		(_gl.FRAGMENT_SHADER, _MAIN_FRAG_SHADER),
	],
	"linear_gradient": [
		(_gl.VERTEX_SHADER,   _VERT_SHADER),
		(_gl.FRAGMENT_SHADER, _GRADIENT_FRAG_SHADER),
		(_gl.FRAGMENT_SHADER, _LINEAR_OFFSET_FRAG_SHADER),
		(_gl.FRAGMENT_SHADER, _MAIN_FRAG_SHADER),
	],
	"radial_gradient": [
		(_gl.VERTEX_SHADER,   _VERT_SHADER),
		(_gl.FRAGMENT_SHADER, _GRADIENT_FRAG_SHADER),
		(_gl.FRAGMENT_SHADER, _RADIAL_OFFSET_FRAG_SHADER),
		(_gl.FRAGMENT_SHADER, _MAIN_FRAG_SHADER),
	],
}


_programs = {}
def _program(name):
	global _programs
	try:
		program = _programs[name]
	except KeyError:
		shaders = (create_shader(*shader) for shader in _shaders[name])
		program = _programs[name] = create_program(*shaders)
	return program


_current_kwargs = {}
_current_program = None

def _create(name, **default_uniforms):
	def _use(**kwargs):
		global _current_program, _current_uniforms
		uniforms = dict(default_uniforms)
		uniforms.update(kwargs)

		program = _program(name)
		if _current_program != program:
			_gl.UseProgram(program)
			_current_program = program
			_current_uniforms = {}
		
		for k in uniforms:
			v = uniforms[k]
			if v != _current_uniforms.get(k, None):
				set_uniform(program, k, v)
		_current_uniforms = uniforms
		
		set_uniform(program, "masking", [len(_MaskContext.textures) > 1])
	return _use

_use_solid_color     = _create("solid_color", mask=[1])
_use_texture         = _create("texture", texture=[0], mask=[1])
_use_linear_gradient = _create("linear_gradient", mask=[1])
_use_radial_gradient = _create("radial_gradient", mask=[1])


# utils ######################################################################

_BASE = 255.
def _float(i, base=_BASE):
	"""convert byte color components to float"""
	return float(i/base if isinstance(i, int) else i)

def _stop(o, c, a=1.):
	"""add optional alpha to gradient stop definitions"""
	if c is Color.none:
		c = Color.black
		a = 0.
	return (float(o), (c._r, c._g, c._b, a))


def _object_bbox(origin, bbox):
	(x_min, y_min), (x_max, y_max) = bbox
	return [Translate(x_min, y_min), Scale(x_max-x_min, y_max-y_min)]

def _user_space(origin, bbox):
	x, y = origin
	return [Translate(-x, -y)]


_UNITS = {
	"objectBoundingBox": _object_bbox,
	"userSpaceOnUse":    _user_space,
}

def _stencil_one(n, vertices):
	_gl.VertexPointer(2, _gl.FLOAT, 0, vertices)
	_gl.StencilOp(_gl.KEEP, _gl.KEEP, _gl.INCR)
	_gl.DrawArrays(_gl.TRIANGLE_STRIP, 0, n)

def _stencil_evenodd(n, vertices):
	_gl.VertexPointer(2, _gl.FLOAT, 0, vertices)
	_gl.StencilOp(_gl.KEEP, _gl.KEEP, _gl.INVERT)
	_gl.DrawArrays(_gl.TRIANGLE_STRIP, 0, n)

def _stencil_nonzero(n, vertices):
	_gl.VertexPointer(2, _gl.FLOAT, 0, vertices)
	_gl.Enable(_gl.CULL_FACE)
	for cull, op in [(_gl.BACK,  _gl.INCR_WRAP),
	                 (_gl.FRONT, _gl.DECR_WRAP)]:
		_gl.CullFace(cull)
		_gl.StencilOp(_gl.KEEP, _gl.KEEP, op)
		_gl.DrawArrays(_gl.TRIANGLE_STRIP, 0, n)
	_gl.Disable(_gl.CULL_FACE)


def _make_paint(_stencil):
	def paint(color, alpha, data, origin, bbox, margin=0.):
		color._use_program()
		_gl.Color(color._r, color._g, color._b, alpha)

		# render mask
		_gl.ColorMask(_gl.FALSE, _gl.FALSE, _gl.FALSE, _gl.FALSE)
		_gl.DepthMask(_gl.FALSE)
		_gl.StencilFunc(_gl.ALWAYS, 0, -1)
		_stencil(*data)
		
		# fill mask
		_gl.ColorMask(_gl.TRUE, _gl.TRUE, _gl.TRUE, _gl.TRUE)
		_gl.DepthMask(_gl.TRUE)
		_gl.StencilFunc(_gl.NOTEQUAL, 0, -1)
		_gl.StencilOp(_gl.KEEP, _gl.KEEP, _gl.REPLACE)
		
		_gl.MatrixMode(_gl.TEXTURE)
		with TransformList(color.units(origin, bbox) + color.transform):
			(x_min, y_min), (x_max, y_max) = bbox
			_gl.Rectf(x_min-margin, y_min-margin,
			          x_max+margin, y_max+margin)
		_gl.MatrixMode(_gl.MODELVIEW)
	return paint


# solid color ################################################################

class _Paint(_Element):
	_r, _g, _b = 1., 1., 1.
	units = staticmethod(_UNITS["objectBoundingBox"])
	transform = []
	
	def get_rgb(self):
		return self._r, self._g, self._b
	def set_rgb(self, rgb):
		self._r, self._g, self._b = rgb
	rgb = property(get_rgb, set_rgb)
	
	paint_one     = _make_paint(_stencil_one)
	paint_evenodd = _make_paint(_stencil_evenodd)
	paint_nonzero = _make_paint(_stencil_nonzero)


class Color(_Paint):
	tag = "solidColor"

	_state_attributes = _Paint._state_attributes + [
		"_r", "_g", "_b",
	]
	
	def __init__(self, r=0., g=None, b=None, name=""):
		self._r = _float(r)
		self._g = _float(g) if g != None else self._r
		self._b = _float(b) if b != None else self._r
		self._name = name

	def _use_program(self):
		_use_solid_color()
	
	def _xml_attr(self, defs):
		return self._name or \
		       "#%02x%02x%02x" % tuple(int(v*_BASE)
		                               for v in self.rgb)


# texture ####################################################################

class _Texture(_Paint):
	def __init__(self, texture_id=0, color=Color(1., 1., 1.)):
		self.texture_id = texture_id
		self.rgb = color.rgb
	
	def __del__(self):
		_gl.DeleteTextures([self.texture_id])
	
	def _use_program(self):
		_gl.BindTexture(_gl.TEXTURE_2D, self.texture_id)
		_use_texture()


class _MaskContext(_Context):
	textures = [0]
	
	def __init__(self, origin, size, texture_id):
		self.origin = origin
		self.size = size
		self.texture_id = texture_id
	
	def __del__(self):
		_gl.DeleteTextures([self.texture_id])

	def enter(self):
		self.textures.append(self.texture_id)
		_gl.ActiveTexture(_gl.TEXTURE1)
		_gl.BindTexture(_gl.TEXTURE_2D, self.texture_id)
		_gl.MatrixMode(_gl.TEXTURE)
		_gl.PushMatrix()
		_gl.LoadIdentity()
		x, y = self.origin
		w, h = self.size
		_gl.Translate(x, y, 0.)
		_gl.Scale(w, h, 1.)
		_gl.ActiveTexture(_gl.TEXTURE0)
		_gl.MatrixMode(_gl.MODELVIEW)

	def exit(self):
		assert self.textures.pop() == self.texture_id
		_gl.ActiveTexture(_gl.TEXTURE1)
		_gl.BindTexture(_gl.TEXTURE_2D, self.textures[-1])
		_gl.MatrixMode(_gl.TEXTURE)
		_gl.PopMatrix()
		_gl.ActiveTexture(_gl.TEXTURE0)
		_gl.MatrixMode(_gl.MODELVIEW)


# pserver ####################################################################

class _PaintServer(_Paint):
	_state_attributes = _Paint._state_attributes + [
		"parent",
	]
	
	def __init__(self, parent=None):
		self.parent = parent

	def __getattr__(self, attribute):
		try:
			return getattr(self.parent, attribute)
		except AttributeError:
			pass
		if attribute in self._DEFAULTS:
			return self._DEFAULTS[attribute]
		return super(_PaintServer, self).__getattribute__(attribute)

	@property
	def id(self):
		return "%X" % id(self)
	
	@property
	def href(self):
		return self.parent

	@property
	def attributes(self):
		attributes = ["id"]
		attributes += list(k for k in self._DEFAULTS if k in dir(self))
		if self.parent:
			attributes += ["href"]
		return attributes


# gradients ##################################################################

_SPREADS = {
	"pad":     0,
	"reflect": 1,
	"repeat":  2,
}

class _Gradient(_PaintServer):
	_DEFAULTS = {
		"stops":             [(0., None)],
		"gradientTransform": [],
		"gradientUnits":     "objectBoundingBox",
		"spreadMethod":      "pad",
	}
	
	_state_attributes = _PaintServer._state_attributes + list(_DEFAULTS) + [
		"stops",
	]

	def __init__(self, stops=None, parent=None, spreadMethod=None,
	                   gradientUnits=None, gradientTransform=None):
		if stops != None: self.stops = stops
		super(_Gradient, self).__init__(parent)
		if spreadMethod != None: self.spreadMethod = spreadMethod
		if gradientUnits != None: self.gradientUnits = gradientUnits
		if gradientTransform != None: self.gradientTransform = gradientTransform
	
	@property
	def units(self):
		return _UNITS[self.gradientUnits]
	
	@property
	def transform(self):
		return self.gradientTransform
	
	def _use_gradient(self, n, os, colors, spread):
		raise NotImplementedError
	
	def _use_program(self):
		n = len(self.stops)
		assert n <= MAX_STOPS, "too much stops in gradient"
		
		os, colors = zip(*(_stop(*stop) for stop in self.stops))
		spread = _SPREADS[self.spreadMethod]
		self._use_gradient(n, os, colors, spread)


	@property
	def attributes(self):
		attributes = super(_Gradient, self).attributes
		if "stops" in attributes:
			attributes.remove("stops")
		return attributes
	
	def _xml_content(self, defs):
		if not "stops" in dir(self):
			return ""
		stops = []
		def _stop(offset, color, opacity=None):
			return offset, color._xml_attr(defs) if color else "none", opacity
		for stop in self.stops:
			offset, color, opacity = _stop(*stop)
			if opacity is None:
				stop = "<stop offset='%s' stop-color='%s' />" % (offset, color)
			else:
				stop = "<stop offset='%s' stop-color='%s' stop-opacity='%s' />" % (offset, color, opacity)
			stops.append(stop)
		return "\n".join(stops)


class LinearGradient(_Gradient):
	tag = "linearGradient"
	
	_DEFAULTS = {
		"x1": 0.,
		"y1": 0.,
		"x2": 1.,
		"y2": 0.,
	}
	_state_attributes = _Gradient._state_attributes + list(_DEFAULTS)

	_DEFAULTS.update(_Gradient._DEFAULTS)
	
	def __init__(self, stops=None, parent=None, spreadMethod=None,
	                   gradientUnits=None, gradientTransform=None,
	                   x1=None, y1=None, x2=None, y2=None):
		super(LinearGradient, self).__init__(stops, parent, spreadMethod,
		                                     gradientUnits, gradientTransform)
		if x1 != None: self.x1 = x1
		if y1 != None: self.y1 = y1
		if x2 != None: self.x2 = x2
		if y2 != None: self.y2 = y2
	
	def _use_gradient(self, n, os, colors, spread):
		_use_linear_gradient(p1=[(float(self.x1), float(self.y1))],
		                     p2=[(float(self.x2), float(self.y2))],
		                     n=[n], os=list(os), colors=list(colors),
		                     spread=[spread])


class RadialGradient(_Gradient):
	tag = "radialGradient"
	
	_DEFAULTS = {
		"cx": .5,
		"cy": .5,
		"r":  .5,
		"fx": None,
		"fy": None,
	}
	_state_attributes = _Gradient._state_attributes + list(_DEFAULTS)

	_DEFAULTS.update(_Gradient._DEFAULTS)
	
	def __init__(self, stops=None, parent=None, spreadMethod=None,
	                   gradientUnits=None, gradientTransform=None,
	                   cx=None, cy=None, r=None, fx=None, fy=None):
		super(RadialGradient, self).__init__(stops, parent, spreadMethod,
		                                     gradientUnits, gradientTransform)
		if cx != None: self.cx = cx
		if cy != None: self.cy = cy
		if r != None: self.r = r
		if fx != None: self.fx = fx
		if fy != None: self.fy = fy
	
	def _use_gradient(self, n, os, colors, spread):
		fx, fy = self.fx, self.fy
		if fx is None: fx = self.cx
		if fy is None: fy = self.cy

		_use_radial_gradient(c=[(float(self.cx), float(self.cy))],
		                     r=[float(self.r)],
		                     f=[(float(fx), float(fy))],
		                     n=[n], os=list(os), colors=list(colors),
		                     spread=[spread])


# pattern ####################################################################

class Pattern(_PaintServer):
	tag = "pattern"
	_r, _g, _b = .5, .5, .5

	_DEFAULTS = {
		"patternTransform": [],
		"patternUnits":     "objectBoundingBox",
		"x": 0.,
		"y": 0.,
		"width": 0.,
		"height": 0.,
	}
	
	_state_attributes = _Paint._state_attributes + list(_DEFAULTS) + [
		"pattern",
	]
	
	def __init__(self, pattern=None, parent=None,
	                   x=None, y=None, width=None, height=None,
	                   patternUnits=None, patternTransform=None,
	                   **kwargs):
		self.pattern = pattern
		super(Pattern, self).__init__(parent)
		if x != None: self.x = x
		if y != None: self.y = y
		if width != None: self.width = width
		if height != None: self.height = height
		if patternUnits != None: self.patternUnits = patternUnits
		if patternTransform != None: self.patternTransform = patternTransform
	
	def _use_program(self):
		_use_solid_color()
	
	def _xml_content(self, defs):
		return self.pattern._xml_content(defs)


# colors by name #############################################################

# see <http://www.w3.org/TR/SVG/types.html#ColorKeywords>

_color_keywords = {
	"aliceblue":            (240, 248, 255),
	"antiquewhite":         (250, 235, 215),
	"aqua":                 (  0, 255, 255),
	"aquamarine":           (127, 255, 212),
	"azure":                (240, 255, 255),
	"beige":                (245, 245, 220),
	"bisque":               (255, 228, 196),
	"black":                (  0,   0,   0),
	"blanchedalmond":       (255, 235, 205),
	"blue":                 (  0,   0, 255),
	"blueviolet":           (138,  43, 226),
	"brown":                (165,  42,  42),
	"burlywood":            (222, 184, 135),
	"cadetblue":            ( 95, 158, 160),
	"chartreuse":           (127, 255,   0),
	"chocolate":            (210, 105,  30),
	"coral":                (255, 127,  80),
	"cornflowerblue":       (100, 149, 237),
	"cornsilk":             (255, 248, 220),
	"crimson":              (220,  20,  60),
	"cyan":                 (  0, 255, 255),
	"darkblue":             (  0,   0, 139),
	"darkcyan":             (  0, 139, 139),
	"darkgoldenrod":        (184, 134,  11),
	"darkgray":             (169, 169, 169),
	"darkgreen":            (  0, 100,   0),
	"darkgrey":             (169, 169, 169),
	"darkkhaki":            (189, 183, 107),
	"darkmagenta":          (139,   0, 139),
	"darkolivegreen":       ( 85, 107,  47),
	"darkorange":           (255, 140,   0),
	"darkorchid":           (153,  50, 204),
	"darkred":              (139,   0,   0),
	"darksalmon":           (233, 150, 122),
	"darkseagreen":         (143, 188, 143),
	"darkslateblue":        ( 72,  61, 139),
	"darkslategray":        ( 47,  79,  79),
	"darkslategrey":        ( 47,  79,  79),
	"darkturquoise":        (  0, 206, 209),
	"darkviolet":           (148,   0, 211),
	"deeppink":             (255,  20, 147),
	"deepskyblue":          (  0, 191, 255),
	"dimgray":              (105, 105, 105),
	"dimgrey":              (105, 105, 105),
	"dodgerblue":           ( 30, 144, 255),
	"firebrick":            (178,  34,  34),
	"floralwhite":          (255, 250, 240),
	"forestgreen":          ( 34, 139,  34),
	"fuchsia":              (255,   0, 255),
	"gainsboro":            (220, 220, 220),
	"ghostwhite":           (248, 248, 255),
	"gold":                 (255, 215,   0),
	"goldenrod":            (218, 165,  32),
	"gray":                 (128, 128, 128),
	"grey":                 (128, 128, 128),
	"green":                (  0, 128,   0),
	"greenyellow":          (173, 255,  47),
	"honeydew":             (240, 255, 240),
	"hotpink":              (255, 105, 180),
	"indianred":            (205,  92,  92),
	"indigo":               ( 75,   0, 130),
	"ivory":                (255, 255, 240),
	"khaki":                (240, 230, 140),
	"lavender":             (230, 230, 250),
	"lavenderblush":        (255, 240, 245),
	"lawngreen":            (124, 252,   0),
	"lemonchiffon":         (255, 250, 205),
	"lightblue":            (173, 216, 230),
	"lightcoral":           (240, 128, 128),
	"lightcyan":            (224, 255, 255),
	"lightgoldenrodyellow": (250, 250, 210),
	"lightgray":            (211, 211, 211),
	"lightgreen":           (144, 238, 144),
	"lightgrey":            (211, 211, 211),
	"lightpink":            (255, 182, 193),
	"lightsalmon":          (255, 160, 122),
	"lightseagreen":        ( 32, 178, 170),
	"lightskyblue":         (135, 206, 250),
	"lightslategray":       (119, 136, 153),
	"lightslategrey":       (119, 136, 153),
	"lightsteelblue":       (176, 196, 222),
	"lightyellow":          (255, 255, 224),
	"lime":                 (  0, 255,   0),
	"limegreen":            ( 50, 205,  50),
	"linen":                (250, 240, 230),
	"magenta":              (255,   0, 255),
	"maroon":               (128,   0,   0),
	"mediumaquamarine":     (102, 205, 170),
	"mediumblue":           (  0,   0, 205),
	"mediumorchid":         (186,  85, 211),
	"mediumpurple":         (147, 112, 219),
	"mediumseagreen":       ( 60, 179, 113),
	"mediumslateblue":      (123, 104, 238),
	"mediumspringgreen":    (  0, 250, 154),
	"mediumturquoise":      ( 72, 209, 204),
	"mediumvioletred":      (199,  21, 133),
	"midnightblue":         ( 25,  25, 112),
	"mintcream":            (245, 255, 250),
	"mistyrose":            (255, 228, 225),
	"moccasin":             (255, 228, 181),
	"navajowhite":          (255, 222, 173),
	"navy":                 (  0,   0, 128),
	"oldlace":              (253, 245, 230),
	"olive":                (128, 128,   0),
	"olivedrab":            (107, 142,  35),
	"orange":               (255, 165,   0),
	"orangered":            (255,  69,   0),
	"orchid":               (218, 112, 214),
	"palegoldenrod":        (238, 232, 170),
	"palegreen":            (152, 251, 152),
	"paleturquoise":        (175, 238, 238),
	"palevioletred":        (219, 112, 147),
	"papayawhip":           (255, 239, 213),
	"peachpuff":            (255, 218, 185),
	"peru":                 (205, 133,  63),
	"pink":                 (255, 192, 203),
	"plum":                 (221, 160, 221),
	"powderblue":           (176, 224, 230),
	"purple":               (128,   0, 128),
	"red":                  (255,   0,   0),
	"rosybrown":            (188, 143, 143),
	"royalblue":            ( 65, 105, 225),
	"saddlebrown":          (139,  69,  19),
	"salmon":               (250, 128, 114),
	"sandybrown":           (244, 164,  96),
	"seagreen":             ( 46, 139,  87),
	"seashell":             (255, 245, 238),
	"sienna":               (160,  82,  45),
	"silver":               (192, 192, 192),
	"skyblue":              (135, 206, 235),
	"slateblue":            (106,  90, 205),
	"slategray":            (112, 128, 144),
	"slategrey":            (112, 128, 144),
	"snow":                 (255, 250, 250),
	"springgreen":          (  0, 255, 127),
	"steelblue":            ( 70, 130, 180),
	"tan":                  (210, 180, 140),
	"teal":                 (  0, 128, 128),
	"thistle":              (216, 191, 216),
	"tomato":               (255,  99,  71),
	"turquoise":            ( 64, 224, 208),
	"violet":               (238, 130, 238),
	"wheat":                (245, 222, 179),
	"white":                (255, 255, 255),
	"whitesmoke":           (245, 245, 245),
	"yellow":               (255, 255,   0),
	"yellowgreen":          (154, 205,  50),
}
for name in _color_keywords:
	r, g, b = _color_keywords[name]
	color = Color(r=r, g=g, b=b, name=name)
	setattr(Color, name, color)

Color.none = None
Color.current = "currentColor"
