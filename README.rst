=======
seagull
=======

a 2D scene graph based on SVG with OpenGL backend


Goals & non-goals
-----------------

Goals:

- 2d scene graph suitable for interactive rendering
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


SVG spec
--------

implemented:

- shapes: path, rect, circle, ellipse, line, polyline, polygon
- structure: group, use (including attributes inheritance)
- painting: solid color, linear and radial gradients (including units, transform, spread, href);
- fill: rule (nonzero, evenodd)
- stroke: cap (butt, round, square), join (miter, round, bevel), miterlimit
- multi-pass rendering: clipping, masking, object opacity
- transforms: translate, rotate, scale, skewX, skewY


eventually:

- shapes: text, tspan, image
- painting: pattern
- stroke: dash, marker
- filters


never:

- DOM API

