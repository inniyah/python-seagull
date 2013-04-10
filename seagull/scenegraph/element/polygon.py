# -*- coding: utf-8 -*-

"""
scenegraph.element.polygon
"""


# imports ####################################################################

from .path import Path


# polygon ####################################################################

class Polygon(Path):
	tag = "polygon"
	
	points = []
	
	@property
	def d(self):
		d = ['M']
		for point in self.points:
			d += [point, 'L']
		d[-1] = 'Z'
		return d
