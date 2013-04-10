# -*- coding: utf-8 -*-

"""
scenegraph.element.polyline
"""


# imports ####################################################################

from .path import Path


# polyline ###################################################################

class Polyline(Path):
	tag = "polyline"
	
	points = []
	
	@property
	def d(self):
		d = ['M']
		for point in self.points:
			d += [point, 'L']
		d.pop()
		return d
