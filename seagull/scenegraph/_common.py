# -*- coding: utf-8 -*-

"""
misc utility functions and classes
"""


# utils ######################################################################

def _indent(s, level=1, tab="\t"):
	"""indent blocks"""
	indent = tab * level
	return "\n".join("%s%s" % (indent, line) for line in s.split("\n"))

def _u(v, encoding="utf8"):
	"""provides a unicode string from anything."""
	if isinstance(v, str):
		return v
	elif isinstance(v, (list, tuple)):
		return " ".join(_u(vi, encoding) for vi in v)
	elif v is None:
		return "none"
	else:
		return str(v)


# base classes ###############################################################

class _Base(object):
	"""equality based on state rather than id"""
	
	_state_attributes = []
	def _state(self):
		return {name: getattr(self, name)
		        for name in self._state_attributes}
	def __eq__(self, other):
		try:
			return other._state() == self._state()
		except AttributeError:
			return False
	def __ne__(self, other): return not self.__eq__(other)
#	def __hash__(self): return hash(self._state())
	def __hash__(self): raise RuntimeError("state is not hashable")


class _Element(_Base):
	"""element with xml serialization support"""
	
	_state_attributes = ["tag"]
	attributes = []
	
	def _xml(self, defs):
		"""xml serialization"""
		u = "<%s %s" % (self.tag, self._xml_attributes(defs))
		content = self._xml_content(defs)
		if content.strip():
			u += ">\n" + \
			     _indent(content) + "\n" + \
			     "</%s>" % self.tag
		else:
			u += "/>"
		return u
	
	def _xml_content(self, defs):
		"""xml serialization of content"""
		return ""
	
	def _xml_attributes(self, defs):
		"""xml serialization of attributes"""
		return " ".join(self._xml_attribute(name, defs) for name in self.attributes)
	
	def _xml_attribute(self, name, defs):
		"""unicode serialization of attribute/value pair"""
		attribute = getattr(self, name)
		if name == "href":
			name = "xlink:href"
			try:
				href = "#%s" % attribute.id
			except:
				pass
			else:
				defs.append(attribute)
				attribute = href
		try:
			u = attribute._xml_attr(defs)
		except AttributeError:
			u = _u(attribute)
		return "%s='%s'" % (name.replace("_", "-"), u) if u else ""
	
	def _xml_attr(self, defs):
		defs.append(self)
		return "url(#%s)" % self.id
