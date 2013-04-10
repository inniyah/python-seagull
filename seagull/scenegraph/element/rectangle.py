# -*- coding: utf-8 -*-

"""
scenegraph.element.rectangle
"""


# imports ####################################################################

from .path import Path


# rectangle ##################################################################

class Rectangle(Path):
	tag = "rect"
	
	width, height = 0, 0
	rx, ry = None, None
	
	@property
	def d(self):
		w, h = self.width, self.height
		if w <= 0. or h <= 0.:
			return []
		
		rx, ry = self.rx, self.ry
		if rx is None and ry is None:
			return ['M', (0, 0), 'l', (0,  h),
			        'l', (w, 0), 'l', (0, -h), 'z']
		
		if rx is None: rx = ry
		if ry is None: ry = rx
		
		rx, ry = min(rx, w/2.), min(ry, h/2.)
		
		return ['M', (0, ry),
		        'L', (0, h-ry), 'A', (rx, ry), 0, (0, 0), (rx, h),
		        'L', (w-rx, h), 'A', (rx, ry), 0, (0, 0), (w, h-ry),
		        'L', (w, ry),   'A', (rx, ry), 0, (0, 0), (w-rx, 0),
		        'L', (rx, 0),   'A', (rx, ry), 0, (0, 0), (0, ry),
		        'Z']
