# -*- coding: utf-8 -*-

"""
scenegraph.element.use
"""


# imports ####################################################################

from . import Element


# use ########################################################################

class Use(Element):
	tag = "use"
	
	_state_attributes = Element._state_attributes + [
		"href",
	]
	
	def __init__(self, element=None, **attributes):
		super(Use, self).__init__(**attributes)
		self.element = element
		self._attributes.add("href")
	
	@property
	def href(self):
		return self.element
		
	def _aabbox(self, transforms, inheriteds):
		return self.element.aabbox(transforms, inheriteds)
	
	def _render(self, transforms, inheriteds):
		self.element.render(transforms, inheriteds)

	def _pick_content(self, x, y, z, transforms):
		return self.element.pick(x, y, z, transforms)
