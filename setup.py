# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
metadata = {
	"name":         'seagull',
	"version":      '0.1',
	"description":  '2D scene graph based on SVG with OpenGL backend',
	"author":       'Renaud Blanch',
	"author_email": 'blanch@imag.fr',
	"url":          'http://bitbucket.org/rndblnch/seagull',
	"packages":     find_packages(),
}

setup(**metadata)
