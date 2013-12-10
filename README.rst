=======
seagull
=======

a 2D scene graph based on SVG with OpenGL backend


Goals & non-goals
-----------------

Goals:

- 2D scene graph suitable for interactive rendering
- minimal set of dependencies


Non-goals:

- full SVG implementation
- optimized for speed


Features
--------

- pythonic API modeled after SVG spec & semantic
- SVG parsing and serialization
- scale dependent polygonalization
- analytical picking
- sub-pixel strokes rendering enhancement through width and opacity correction
- per-pixel gradients
- two modes text rendering: raster by freetype2 for high quality AA at small sizes, vector otherwise


SVG spec
--------

implemented:

- shapes: path, rect, circle, ellipse, line, polyline, polygon, image
- text: (excluding decoration, text on path)
- structure: group, use (including attributes inheritance)
- painting: solid color, linear and radial gradients (including units, transform, spread, href);
- fill: rule (nonzero, evenodd)
- stroke: cap (butt, round, square), join (miter, round, bevel), miterlimit
- multi-pass rendering: clipping, masking, object opacity
- transforms: translate, rotate, scale, skewX, skewY


eventually:

- tspan
- painting: pattern
- stroke: dash, marker
- filters


never:

- DOM API


Dependencies
------------

- PyOpenGL_ 3.0.2+ OpenGL python bindings
- Pillow_ 2+ Python Imaging Library (fork)
- freetype2_ font engine
- `GNU FreeFont`_ Free UCS Outline Fonts

.. _PyOpenGL: https://pypi.python.org/pypi/PyOpenGL
.. _Pillow: https://pypi.python.org/pypi/Pillow
.. _freetype2: http://www.freetype.org/freetype2/
.. _GNU FreeFont: http://savannah.gnu.org/projects/freefont/


Optional dependencies
---------------------

Needed to find fonts, fallbacks on FreeFont otherwise.

on the mac:

- pyobjc-framework-CoreText_ wrappers for the framework CoreText on Mac OS X

.. _pyobjc-framework-CoreText: https://pypi.python.org/pypi/pyobjc-framework-CoreText/



Inspirations
------------

- sauvage_ by S. Conversy
- SVGL_ by S. Conversy & J.-D. Fekete

.. _sauvage: http://lii-enac.fr/~conversy/research/sauvage/
.. _SVGL:    http://lii-enac.fr/~conversy/research/svgl/
