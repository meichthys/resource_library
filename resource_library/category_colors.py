# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

"""A colour for every category: one dark base per root, lighter under it.

Colour carries the taxonomy rather than the individual category. Each root gets
a base from the palette below, and everything filed under that root gets the
same hue mixed with white, a step per level down. So a chip on a card says which
branch a resource belongs to before the label is read, and two categories in
different branches never look alike.
"""

import re

import frappe

# One dark base per root category, handed out in the order below. Ordered so
# neighbouring entries sit far apart on the colour wheel, since the roots taken
# first are the ones a small site actually shows. Each is dark enough to carry
# white text, which is what the chips, swatches and icon placeholders all use.
ROOT_PALETTE = (
	"#1d4e8f",  # blue
	"#7d4f0c",  # amber
	"#186b4a",  # green
	"#8c2f4a",  # crimson
	"#3a2f8c",  # violet
	"#0f5f6e",  # teal
	"#8f3c1e",  # burnt orange
	"#6d2f7a",  # purple
	"#4f5c10",  # olive
)

# How far towards white each level below the root moves, and how many levels
# keep moving. The cap is what keeps a deep branch readable: past two steps the
# shade is pale enough that white text on it starts to fail, so anything deeper
# holds at the level two colour rather than fading out.
LIGHTEN_STEP = 0.16
MAX_LIGHTER_LEVELS = 2

# What an element carrying a category the map does not cover falls back to, and
# what a resource with no category at all gets. Neutral on purpose: it reads as
# unclassified rather than as a branch of its own.
FALLBACK_COLOR = "#3f3f46"

# Anything outside this set is written as a CSS escape when a category name goes
# into a selector. Names are free text an admin or a submitter typed, so they
# reach the stylesheet as data: a quote or an angle bracket left literal would
# end the selector, or the <style> element itself.
CSS_SAFE = re.compile(r"[^\w \-]", re.UNICODE)


def lighten(color, amount):
	"""`color` mixed with white, `amount` being the fraction of the way there."""
	channels = (int(color[index : index + 2], 16) for index in (1, 3, 5))
	return "#%02x%02x%02x" % tuple(round(c + (255 - c) * amount) for c in channels)


def get_category_colors():
	"""Map of every category name to the colour it is drawn in.

	Roots are sorted by name before the palette is handed out, so the colours
	are the same on every request and in every process. The cost is that adding
	a root re-cuts the deck for the roots after it alphabetically, which is the
	right way round: a taxonomy this size changes rarely, and a root sharing a
	colour with its neighbour would be wrong every day in between.

	Walked from the roots down through parent_category rather than by lft/rgt,
	the same reasoning as get_category_path: the nested set boundaries here have
	repeatedly drifted out of sync after ordinary edits.
	"""
	rows = frappe.get_all("Category", fields=["name", "parent_category"], order_by="name asc")

	names = {row.name for row in rows}
	children_by_parent = {}
	roots = []
	for row in rows:
		# A category whose parent was deleted is a root as far as colour goes,
		# since nothing above it can lend it one.
		if row.parent_category and row.parent_category in names:
			children_by_parent.setdefault(row.parent_category, []).append(row.name)
		else:
			roots.append(row.name)

	colors = {}
	for index, root in enumerate(sorted(roots)):
		base = ROOT_PALETTE[index % len(ROOT_PALETTE)]
		colors[root] = base

		# Breadth first from the root, so depth is settled the first time a
		# category is reached. `seen` guards the cycle a parent_category loop
		# would otherwise spin in.
		queue = [(child, 1) for child in children_by_parent.get(root, [])]
		seen = {root}
		while queue:
			name, depth = queue.pop(0)
			if name in seen:
				continue

			seen.add(name)
			colors[name] = lighten(base, min(depth, MAX_LIGHTER_LEVELS) * LIGHTEN_STEP)
			queue.extend((child, depth + 1) for child in children_by_parent.get(name, []))

	return colors


def get_category_color_css():
	"""The category colours as CSS, one custom property rule per category.

	A rule rather than an inline style on every chip: the colour is then set
	once per page and inherited, so an element only has to say which category it
	is about and any descendant of it can draw in that colour. The match is
	case-insensitive because a card carries the lowercased name for the search
	filter to read, while the chips carry it as written.
	"""
	rules = []
	for name, color in sorted(get_category_colors().items()):
		selector = CSS_SAFE.sub(lambda match: "\\%06x " % ord(match.group()), name)
		rules.append(f'[data-category="{selector}" i]{{--cat-color:{color}}}')

	return "\n".join(rules)
