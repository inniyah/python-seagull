# -*- coding: utf8 -*-

"""svg serialization"""


# serialization ##############################################################

_SVG_HEADER = """\
<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE svg PUBLIC '-//W3C//DTD SVG 1.1//EN' 'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd'>
<svg version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'
     viewBox='%s %s %s %s'>"""

_SVG_FOOTER = """\
</svg>
"""

def _indent(s, level=1, tab="\t"):
	"""indent blocks"""
	indent = tab * level
	return "\n".join("%s%s" % (indent, line) for line in s.split("\n"))

def serialize(*elems):
	"""serialization of elems into svg+xml."""
	defs = []
	xml_elems = [_indent(elem._xml(defs)) for elem in elems]
	xml_defs = set()
	while defs:
		elem = defs.pop()
		xml_defs.add(_indent(elem._xml(defs), 2))
	
	(x_min, y_min), (x_max, y_max) = (float("inf"), )*2, (float("-inf"), )*2
	for elem in elems:
		(ex_min, ey_min), (ex_max, ey_max) = elem.aabbox()
		x_min, x_max = min(x_min, ex_min), max(x_max, ex_max)
		y_min, y_max = min(y_min, ey_min), max(y_max, ey_max)

	def xml_lines():
		yield _SVG_HEADER % (x_min, y_min, x_max-x_min, y_max-y_min)
		if xml_defs:
			yield "\t<defs>"
			for xml_def in xml_defs:
				yield xml_def
			yield "\t</defs>"
		for xml_elem in xml_elems:
			yield xml_elem
		yield _SVG_FOOTER
	
	return "\n".join(xml_lines())
