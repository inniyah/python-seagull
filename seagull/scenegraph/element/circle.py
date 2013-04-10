# -*- coding: utf-8 -*-

"""
scenegraph.element.circle
"""


# imports ####################################################################

from .path import Path


# circle #####################################################################

class Circle(Path):
	tag = "circle"
	
	cx, cy = 0, 0
	r = 0
	
	@property
	def d(self):
		cx, cy = self.cx, self.cy
		r = self.r
		return ['M', (cx-r, cy), 'a', (r, r), 0, (0, 0), ( 2*r, 0),
		                         'a', (r, r), 0, (0, 0), (-2*r, 0), 'Z']
