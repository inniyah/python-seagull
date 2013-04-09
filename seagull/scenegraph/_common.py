# -*- coding: utf-8 -*-

"""
misc utility functions and classes
"""


# utils ######################################################################

def _indent(s, level=1, tab=u"\t"):
	"""indent blocks"""
	indent = tab * level
	return u"\n".join(u"%s%s" % (indent, line) for line in s.split(u"\n"))


def _u(v, encoding="utf8"):
	"""provides a unicode string from anything."""
	if isinstance(v, unicode):
		return v
	elif isinstance(v, (list, tuple)):
		return u' '.join(_u(vi, encoding) for vi in v)
	elif v is None:
		return u'none'
	else:
		return unicode(str(v), encoding)


# base classes ###############################################################

class _Base(object):
	"""equality based on state rather than id"""
	
	_state_attributes = []
	def _state(self):
		return dict((name, getattr(self, name)) for name in self._state_attributes)
	def __eq__(self, other):
		try:
			return self._state() == other._state()
		except AttributeError:
			return False
	def __ne__(self, other): return self._state() != other._state()
	def __hash__(self): return hash(self._state())


class _Element(_Base):
	"""element with xml serialization support"""
	
	attributes = []
	
	_state_attributes = ["tag"]
	
	def _xml(self, defs):
		"""xml serialization"""
		u = u"<%s %s" % (self.tag, self._xml_attributes(defs))
		content = self._xml_content(defs)
		if content.strip():
			u += u">\n" + \
			     _indent(content) + u"\n" + \
			     u"</%s>" % self.tag
		else:
			u += u"/>"
		return u
	
	def _xml_content(self, defs):
		"""xml serialization of content"""
		return u""
	
	def _xml_attributes(self, defs):
		"""xml serialization of attributes"""
		return u" ".join(self._xml_attribute(name, defs) for name in self.attributes)
	
	def _xml_attribute(self, name, defs):
		"""unicode serialization of attribute/value pair"""
		attribute = getattr(self, name)
		if name == u"href":
			name = u"xlink:href"
			defs.append(attribute)
			attribute = u"#%s" % attribute.id
		try:
			u = attribute._xml_attr(defs)
		except AttributeError:
			u = _u(attribute)
		return u"%s='%s'" % (name.replace(u'_', u'-'), u) if u else u""
	
	def _xml_attr(self, defs):
		defs.append(self)
		return u"url(#%s)" % self.id


class _Context(_Base):
	"""context manager"""
	
	def __enter__(self):
		return self.enter()
	def __exit__(self, type, value, tb):
		self.exit()
	
	def enter(self): pass
	def exit(self):  pass
