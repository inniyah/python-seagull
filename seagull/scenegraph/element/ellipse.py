# -*- coding: utf-8 -*-

"""
scenegraph.element.ellipse
"""


# imports ####################################################################

from .path import Path


# ellipse ####################################################################

class Ellipse(Path):
	tag = "ellipse"
	
	cx, cy = 0, 0
	rx, ry = 0, 0
	
	@property
	def d(self):
		cx, cy = self.cx, self.cy
		rx, ry = self.rx, self.ry
		if rx <= 0. or ry <= 0.:
			return []
		return ['M', (cx-rx, cy), 'a', (rx, ry), 0, (0, 0), ( 2*rx, 0),
		                          'a', (rx, ry), 0, (0, 0), (-2*rx, 0), 'Z']
