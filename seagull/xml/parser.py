# -*- coding: utf-8 -*-

"""
svg parser
"""

# imports ####################################################################

import sys
import os
import logging
import xml.parsers.expat
import gzip
from tempfile import mkstemp
from base64 import b64decode
from collections import defaultdict

from .. import scenegraph as sg


# logging ####################################################################

log = logging.getLogger(__name__)


# utils ######################################################################

def ascii(v, _=None):
	return str(v)

def number(v, _=None):
	try:
		return int(v)
	except ValueError:
		scale = 1.
		if v.endswith(r"%"):
			scale = 100.
			v = v[:-len(r"%")]
		return float(v) / scale

def replace(s, *pairs):
	for before, after in pairs:
		s = s.replace(before, after)
	return s


# sublanguages ###############################################################

def unquote(v):
	b, e = v[0], v[-1]
	if b == e and b in ["'", '"']:
		v = v[1:-1]
	return v

def attributify(style):
	attributes = [p.strip().split(":") for p in style.split(";") if p]
	return dict((k.strip(), unquote(v.strip())) for (k, v) in attributes)

def styles(cdata):
	styles = defaultdict(dict)
	cdata = replace(cdata, ("{", " { "), ("}", " } "))
	cdata = iter(cdata.split())
	for token in cdata:
		if token == "/*":
			while not next(cdata) == "*/":
				pass
			try:
				token = next(cdata)
			except:
				continue
		while not token.startswith("{"):
			key = token # TODO: properly implement css selectors
			token = next(cdata, "{}")
		content = token
		for token in cdata:
			content += token
			if content.endswith("}"):
				break
		styles[key].update(attributify(content[len("{"):-len("}")]))
	return styles

def asciify_key(k):
	k = ascii(k)
	for c in "-:":
		k = k.replace(c, '_')
	if k in ["id", "class"]:
		k = "_%s" % k
	if k == "xlink_href":
		k = "href"
	return k

def asciify_keys(d):
	return dict((asciify_key(k), d[k]) for k in d)

def switify_values(d, elements):
	return dict((k, converters[k](d[k], elements)) for k in d)

_UNITS = {  # http://www.w3.org/TR/SVG/coords.html#Units
	"px":  1.,
	"pt":  1.25,
	"pc": 15,
	"em": 10,         # TODO: this should be dependant on current font-size
	"ex":  5,         # TODO: this should be dependant on current x-height
	"mm":  3.543307,
	"cm": 35.43307,
	"in": 90.,
}

_SIZE_FACTOR = 1.2
_MEDIUM = 12 * _UNITS["pt"]

_ABSOLUTE_SIZES = {
	"xx-small": _MEDIUM * _SIZE_FACTOR ** -3,
	"x-small":  _MEDIUM * _SIZE_FACTOR ** -2,
	"small":    _MEDIUM * _SIZE_FACTOR ** -1,
	"medium":   _MEDIUM,
	"large":    _MEDIUM * _SIZE_FACTOR ** 1,
	"x-large":  _MEDIUM * _SIZE_FACTOR ** 2,
	"xx-large": _MEDIUM * _SIZE_FACTOR ** 3,
}

def length(v, _=None):
	v = v.lower()
	if v in _ABSOLUTE_SIZES:
		return _ABSOLUTE_SIZES[v]
	
	u = 1.
	unit = v[-2:]
	if unit in _UNITS:
		u = _UNITS[unit]
		v = v[:-2]
	return u * number(v)

def length_list(v, _=None):
	if v == 'none':
		return None
	v = replace(v, (",", " "))
	v = list(length(u) for u in v.split())
	if len(v) == 1:
		return v[0]
	return v

def color(v, elements={}):
	if v == "currentColor":
		v = "current"
	
	if hasattr(sg.Color, v): # named color
		return getattr(sg.Color, v)
	
	if v.startswith("rgb(") and v.endswith(")"): # rgb
		rgb = v[len("rgb("):-len(")")]
		r, g, b = (number(u) for u in rgb.split(","))
		return sg.Color(r, g, b)
	
	if v.startswith("#"): # raw color
		rrggbb = v[len('#'):]
		if len(rrggbb) == 3:
			rrggbb = "".join(c*2 for c in rrggbb)
		rr, gg, bb = rrggbb[:2], rrggbb[2:4], rrggbb[4:]
		return sg.Color(*(int(u, 16) for u in (rr, gg, bb)))
	
	if v.startswith("url(#"): # def
		url = v[len("url(#"):-len(")")]
		if url in elements:
			return get_pserver(elements, url)
	
	log.warning("unknown color %s" % v)
	return "unknown"


def transform(v):
	transform, v = v.split("(")
	Transform = {
		"translate": sg.Translate,
		"rotate":    sg.Rotate,
		"scale":     sg.Scale,
		"skewX":     sg.SkewX,
		"skewY":     sg.SkewY,
		"matrix":    sg.Matrix,
	}[transform]
	return Transform(*(number(u) for u in v.split()))

def transform_list(v, _=None):
	v = replace(v, (" (", "("), (",", " "))
	return [transform(t.strip()) for t in v.split(")")[:-1]]

def url(v, elements={}):
	if v == "none":
		return None
	assert v.startswith("url(#"), v
	url = v[len("url(#"):-len(")")]
	return elements.get(url, str(url))

def href(v, _=None):
	if v.startswith("file://"):
		v = v[len("file://"):]
	elif v.startswith("data:image/"):
		ext, data = v[len("data:image/"):].split(";", 1)
		assert data.startswith("base64,")
		data = data[len("base64,"):]
		data = data.encode("ascii")
		data = b64decode(data)
		try:
			data = gzip.decompress(data)
		except:
			pass
		_, v = mkstemp(".%s" % ext)
		with open(v, "bw") as _image:
			_image.write(data)
	return ascii(v)


_PATH_COMMANDS = "MLVHCSQTAZmlvhcsqtaz"

def pop1(v):
	return number(v.pop())
def pop2(v):
	return (pop1(v), pop1(v))

_POPPERS = defaultdict(list, {
	'M': [pop2],
	'L': [pop2],
	'V': [pop1],
	'H': [pop1],
	'C': [pop2, pop2, pop2],
	'S': [pop2, pop2],
	'Q': [pop2, pop2],
	'T': [pop2],
	'A': [pop2, pop1, pop2, pop2],
})

def path_data(v, _=None):
	v = replace(v, ("-", " -"), ("e -", "e-"),  ("E -", "E-"), (",", " "),
	               *((c, " %s " % c) for c in _PATH_COMMANDS))
	v = list(reversed(v.split()))
	d, last_c = [], 'M'
	while v:
		c = v.pop()
		if c not in _PATH_COMMANDS:
			v.append(c)
			c = last_c
		d.append(c)
		last_c = c
		if last_c == 'M': last_c = 'L'
		if last_c == 'm': last_c = 'l'
		for popper in _POPPERS[c.upper()]:
			d.append(popper(v))
	return d

def point_list(v, _=None):
	v = replace(v, ("-", " -"), ("e -", "e-"),  ("E -", "E-"), (",", " "))
	v = list(reversed(v.split()))
	d = []
	while v:
		try:
			d.append(pop2(v))
		except IndexError:
			break
	return d

converters = defaultdict(lambda: lambda a, _: ascii(a), {
	"x":                 length_list,
	"y":                 length_list,
	"rx":                length,
	"ry":                length,
	"x1":                length,
	"y1":                length,
	"x2":                length,
	"y2":                length,
	"width":             length,
	"height":            length,
	"font_size":         length,
	"stroke_width":      length,
	"stroke_miterlimit": number,
	"stroke_opacity":    number,
	"stroke_dasharray":  length_list,
	"stroke_dashoffset": length,
	"fill_opacity":      number,
	"opacity":           number,
	"color":             color,
	"fill":              color,
	"stroke":            color,
	"transform":         transform_list,
	"clip_path":         url,
	"mask":              url,
	"href":              href,
	"d":                 path_data,
	"points":            point_list,
	"cx":                length,
	"cy":                length,
	"r":                 length,
	"fx":                length,
	"fy":                length,
	"gradientTransform": transform_list,
	"patternTransform":  transform_list,
	"viewBox":           length_list,
})


# gradient ###################################################################

def stop(offset, stop_color="none", stop_opacity=None, **_):
	o, c = number(offset), color(stop_color)
	if stop_opacity is None:
		return o, c
	return o, c, number(stop_opacity)


# parser class ###############################################################

class Parser(object):
	def __init__(self):
		self.expat_parser = xml.parsers.expat.ParserCreate()
		self.expat_parser.StartElementHandler  = self.start_element
		self.expat_parser.EndElementHandler    = self.end_element
		self.expat_parser.CharacterDataHandler = self.char_data
		self.expat_parser.ProcessingInstructionHandler = self.proc_instruction
		self.reset()
	
	def proc_instruction(self, target, data):
		if target != 'xml-stylesheet':
			return
		if not data.startswith('type="text/css"'):
			return
		b = data.find('href="')
		if b < 0:
			return
		b += len('href="')
		e = data.find('"', b)
		css_name = data[b:e]
		style = styles(open(css_name).read())
		self.styles.update(style)
	
	def reset(self, **attributes):
		self.root = sg.Group(**attributes)
		self.groups = [self.root]
		self.elements = {"__root__": self.root}
		self.cdata = []
		self.texts = []
		self.gradient_stops = []
		self.uses = defaultdict(list)
		self.clippeds = defaultdict(list)
		self.maskeds = defaultdict(list)
		self.styles = defaultdict(dict)
	
	def parse(self, document):
		self.expat_parser.Parse(document)
		for _id in self.uses:
			log.warning("undefined reference #%s replaced by empty group" % _id)
			for use in self.uses[_id]:
				use.element = sg.Group()
		for _id in self.clippeds:
			log.warning("undefined clipPath #%s replaced by none" % _id)
			for clipped in self.clippeds[_id]:
				clipped.clip_path = None
		for _id in self.maskeds:
			log.warning("undefined mask #%s replaced by none" % _id)
			for masked in self.maskeds[_id]:
				masked.mask = None
	
	def char_data(self, data):
		self.cdata.append(data)
	
	def start_element(self, name, attributes):
		name = name.split(":")[-1]
		if "style" in attributes:
			style = attributes.pop("style")
			attributes.update(attributify(style))
		if "class" in attributes:
			key = ".%s" % attributes["class"]
			attributes.update(self.styles[key])
		if "id" in attributes:
			key = "#%s" % attributes["id"]
			attributes.update(self.styles[key])
		attributes.update(self.styles[name])
		attributes.update(self.styles["*"])
		
		attributes = asciify_keys(attributes)
		attributes = switify_values(attributes, self.elements)
		for k in "color", "fill", "stroke":
			if attributes.get(k, None) == "unknown":
				del attributes[k]
		
		try:
			handler = getattr(self, "open_%s" % name)
		except AttributeError:
			try:
				handler = {
					"svg":      sg.Group,
					"g":        sg.Group,
					"symbol":   sg.Group,
					"a":        sg.Group,
					"defs":     sg.Group,
					"clipPath": sg.Group,
					"mask":     sg.Group,
					"path":     sg.Path,
					"rect":     sg.Rectangle,
					"circle":   sg.Circle,
					"ellipse":  sg.Ellipse,
					"line":     sg.Line,
					"polyline": sg.Polyline,
					"polygon":  sg.Polygon,
				}[name]
			except KeyError:
				log.warning("unhandeled %s element" % name)
				return
		elem = handler(**attributes)
		if elem is None:
			return
		
		if "clip_path" in attributes:
			clipPath = attributes["clip_path"]
			if isinstance(clipPath, str):
				self.clippeds[clipPath].append(elem)
		
		if "mask" in attributes:
			mask = attributes["mask"]
			if isinstance(mask, str):
				self.maskeds[mask].append(elem)
		
		if "_id" in attributes:
			_id = attributes["_id"]
			self.elements[_id] = elem
			for use in self.uses.pop(_id, []):
				use.element = elem
			for clipped in self.clippeds.pop(_id, []):
				clipped.clip_path = elem
			for masked in self.maskeds.pop(_id, []):
				masked.mask = elem
		
		if name in ["defs", "clipPath", "mask", "pattern"]:
			elem.tag = name
		else:
			self.groups[-1].children.append(elem)
		
		if isinstance(elem, sg.Group):
			self.groups.append(elem)
	
	def end_element(self, name):
		name = name.split(":")[-1]
		try:
			handler = getattr(self, "close_%s" % name)
		except AttributeError:
			pass
		else:
			handler()
	
	
	def close_g(self):
		return self.groups.pop()
	close_symbol = close_g
	close_a = close_g
	close_defs = close_g
	close_svg = close_g
	
	def close_clipPath(self):
		return fix_clip_attributes(self.close_g())
	
	def close_mask(self):
		return fix_mask_attributes(self.close_g())
	
	
	def open_style(self, **attributes):
		self.cdata = []
	
	def close_style(self):
		self.styles.update(styles("".join(self.cdata)))
		self.cdata = []
	
	
	def open_text(self, **attributes):
		text = sg.Text("", **attributes)
		self.texts.append(text)
		self.cdata = []
		return text
	
	def close_text(self):
		text = self.texts.pop()
		text.text = "".join(self.cdata)
	
	
	def open_use(self, **attributes):
		_href = attributes.pop("href")
		try:
			external, _id = _href.split("#")
		except ValueError:
			external, _id = _href, "__root__"
		if external:
			# TODO: cache parsers if the same external file is reused with != _id
			parser = Parser()
			cwd = os.getcwd()
			path, filename = os.path.split(external)
			if path:
				os.chdir(path)
			if filename.endswith('z'):
				f = gzip.open(filename)
			else:
				f = open(filename, "rb")
			try:
				parser.parse(f.read())
			finally:
				f.close()
				os.chdir(cwd)
		else:
			parser = self
		element = parser.elements.get(_id, None)
		use = sg.Use(element, **attributes)
		if element is None:
			self.uses[_id].append(use)
		return use
	
	
	def open_image(self, **attributes):
		href = attributes["href"]
		if "svg" in href.rsplit(".")[-1]:
			return self.open_use(**attributes)
		return sg.Image(**attributes)
	
	
	def open_pserver(self, **attributes):
		self.pserver_kwargs = attributes
	
	def close_pserver(self, PaintServer):
		kwargs = self.pserver_kwargs
		_id = kwargs.pop("_id")
		_href = kwargs.pop("href", None)
		if _href:
			assert _href.startswith("#")
			kwargs["parent"] = _href[len("#"):]
		if self.gradient_stops:
			kwargs["stops"] = [stop(**s) for s in self.gradient_stops]
			self.gradient_stops = []
		self.elements[_id] = (PaintServer, kwargs)
	
	open_linearGradient = open_radialGradient = open_pserver
	def open_pattern(self, **attributes):
		self.open_pserver(**attributes)
		return sg.Group()
	
	def close_linearGradient(self):
		return self.close_pserver(sg.LinearGradient)
	def close_radialGradient(self):
		return self.close_pserver(sg.RadialGradient)
	def close_pattern(self):
		self.pserver_kwargs["pattern"] = self.close_g()
		return self.close_pserver(sg.Pattern)
	
	def open_stop(self, **attributes):
		self.gradient_stops.append(attributes)


def get_pserver(elements, _id):
	pserver = elements[_id]
	
	try:
		PaintServer, kwargs = pserver
	except TypeError:
		pass
	else:
		if "parent" in kwargs:
			parent_id = kwargs["parent"]
			parent = get_pserver(elements, parent_id)
		else:
			parent = None
		pserver = elements[_id] = PaintServer(parent, **{k: kwargs[k] for k in kwargs if k in PaintServer._DEFAULTS})
	
	return pserver

def fix_clip_attributes(clip):
	try:
		clip.fill_rule = clip.clip_rule
	except AttributeError:
		pass
	if isinstance(clip, sg.Group):
		clip.fill = sg.Color.white
		clip.fill_opacity = 1.
		clip.stroke = None
		clip.opacity = 1.
		for child_clip in clip.children:
			fix_clip_attributes(child_clip)
	else:
		for attr in ["fill", "fill_opacity", "stroke", "opacity"]:
			try:
				delattr(clip, attr)
			except AttributeError:
				pass
	return clip

def fix_mask_attributes(mask):
	for attr in ["x", "y", "width", "height"]:
		try:
			delattr(mask, attr)
		except AttributeError:
			pass
	return mask


def parse(document, logging_level=logging.ERROR):
	log.setLevel(logging_level)
	parser = Parser()
	parser.parse(document)
	return parser.root
