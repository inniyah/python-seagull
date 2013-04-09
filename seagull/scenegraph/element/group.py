# -*- coding: utf-8 -*-

"""
scenegraph.element.group
"""


# imports ####################################################################

from . import Element
from ._path import _bbox


# group ######################################################################

_empty_bbox = _bbox([])

class Group(Element):
	tag = u"g"

	_state_attributes = Element._state_attributes + [
		"children",
	]
		
	def __init__(self, children=None, **attributes):
		super(Group, self).__init__(**attributes)
		self.children = children if children != None else []
	
	def _aabbox(self, transforms, inheriteds):
		bboxes = (child.aabbox(transforms, inheriteds) for child in self.children)
		return _bbox(bbox for bbox in bboxes if bbox != _empty_bbox)
	
	def _render(self, transforms, inheriteds):
		for child in self.children:
			child.render(transforms, inheriteds)
					
	def _pick_content(self, x, y, z, transforms):
		hits = []
		for child in self.children:
			hits += child.pick(x, y, z, transforms)
		return hits
		
	def _xml_content(self, defs):
		return u"\n".join(child._xml(defs) for child in self.children)