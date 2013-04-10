# -*- coding: utf-8 -*-

"""
scenegraph.element.line
"""


# imports ####################################################################

from .path import Path


# line #######################################################################

class Line(Path):
	tag = "line"
	
	fill = None
	
	x1, y1 = 0, 0
	x2, y2 = 0, 0
	
	@property
	def d(self):
		return ['M', (self.x1, self.y1), 'L', (self.x2, self.y2)]
