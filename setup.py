# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
metadata = {
	"name":         'seagull',
	"version":      '0.1',
	"description":  '2D scene graph based on SVG with OpenGL backend',
	"author":       'Renaud Blanch',
	"author_email": 'rb@rndblnch.org',
	"url":          'http://bitbucket.org/rndblnch/seagull',
	"license":      'GPLv3+',
	"classifiers":  [
		"""License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)""",
		"""Programming Language :: Python :: 3.3""",
		"""Topic :: Software Development :: Libraries :: Python Modules""",
		"""Topic :: Multimedia :: Graphics""",
	                ],
	"packages":     find_packages(),
}

setup(**metadata)
