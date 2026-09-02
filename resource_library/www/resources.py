from collections import Counter
from urllib.parse import quote

import frappe

from resource_library.resource_library.doctype.resource.resource import (
	CARD_FACT_FIELDS,
	build_card_facts,
	get_approved_category_names,
	get_approved_tag_names,
	get_category_path,
	get_descendant_categories,
	get_tags_by_resource,
)

no_cache = 1


# Kept short so the list reads as a set of choices rather than sentences. An
# <option> cannot hold an SVG, so the icons here are unicode glyphs, and the
# word naming the control is added to the closed display in the template rather
# than repeated down every row of the open list.
SORT_OPTIONS = {
	"alpha": "A-Z",
	"rating": "★ Rating",
}

# Stars a resource has to average before the Top Rated filter keeps it. An
# unrated resource averages 0, so it falls out of that filter on its own.
TOP_RATED_MINIMUM = 4

# Recommended and Top Rated are independent switches, so the dropdown that
# replaced their two pills enumerates the four combinations rather than
# pretending they are alternatives. Four is small enough to read at a glance,
# and it keeps the control a plain select that navigates on change, with no
# script behind it. The trophy and star are the same two marks the pills
# carried, and the same two the cards and star rows use.
#
# Each option carries the sentence the hover explainer shows. A glyph and two
# words say which filter is on but not what it does, and whichever of these is
# in force is usually why a listing came back shorter than expected.
FILTER_OPTIONS = [
	{
		"label": "All",
		"tip": "Showing everything published, whatever it was rated and whether or not an editor has vetted it.",
		"recommended": False,
		"top_rated": False,
	},
	{
		"label": "🏆 Recommended",
		"tip": "Showing only resources an editor has vetted and recommends.",
		"recommended": True,
		"top_rated": False,
	},
	{
		"label": "★ Top Rated",
		"tip": f"Showing only resources averaging {TOP_RATED_MINIMUM} stars or more across their approved reviews.",
		"recommended": False,
		"top_rated": True,
	},
	{
		"label": "🏆 ★ Both",
		"tip": f"Showing only resources an editor recommends that also average {TOP_RATED_MINIMUM} stars or more.",
		"recommended": True,
		"top_rated": True,
	},
]

SORT_TIPS = {
	"alpha": "Ordered by title, A to Z.",
	"rating": (
		"Ordered by average rating. Ties go to the resource more people reviewed, so a lone "
		"five star review does not outrank a well reviewed one."
	),
}


def build_url(category, top_rated, sort, recommended_only, tag):
	params = []
	if category:
		params.append(f"category={quote(category)}")
	if tag:
		params.append(f"tag={quote(tag)}")
	if top_rated:
		params.append("top_rated=1")
	if sort and sort != "alpha":
		params.append(f"sort={sort}")
	if not recommended_only:
		params.append("recommended=0")
	return "/resources" + ("?" + "&".join(params) if params else "")


def build_empty_message(category, tag, recommended_only, top_rated):
	"""Sentence for an empty listing, naming the filters that produced it.

	"Recommended" is on unless a link explicitly turns it off, so it is the
	usual reason a listing comes back empty; spelling the active filters out
	beats leaving a visitor to work out why a category looks bare.
	"""
	parts = ["No resources found"]

	if category:
		parts.append(f"in the {category} category")
	if tag:
		parts.append(f"tagged {tag}")

	qualifiers = []
	if recommended_only:
		qualifiers.append("recommended")
	if top_rated:
		qualifiers.append(f"rated {TOP_RATED_MINIMUM} stars or higher")

	if qualifiers:
		parts.append("that are " + " and ".join(qualifiers))

	return " ".join(parts) + "."


def build_category_tree(counts, url):
	"""Nested taxonomy of the approved categories, for the tree browser.

	Ordered alphabetically at every level rather than by lft/rgt: the nested set
	boundaries on this site have repeatedly drifted out of sync after ordinary
	edits, and an alphabetical tree is the more predictable thing to scan.

	Each node carries the number of resources in its whole branch, counted under
	the filters currently in force, so the number beside a category is what
	choosing it would actually show rather than a total that ignores the
	Recommended and Top Rated toggles.
	"""
	rows = frappe.get_all(
		"Category",
		filters={"status": "Approved"},
		fields=["name", "category as label", "parent_category"],
		order_by="category asc",
	)

	children_by_parent = {}
	for row in rows:
		children_by_parent.setdefault(row.parent_category or None, []).append(row)

	def build(row, seen):
		# A cycle in parent_category would otherwise recurse until the stack
		# gives out, and this tree is rendered on the site's busiest page.
		if row.name in seen:
			return None

		branch_seen = seen | {row.name}
		children = [
			node
			for node in (build(child, branch_seen) for child in children_by_parent.get(row.name, []))
			if node
		]

		return {
			"name": row.name,
			"label": row.label,
			"url": url(category=row.name),
			"count": counts.get(row.name, 0) + sum(child["count"] for child in children),
			"children": children,
		}

	return [node for node in (build(row, set()) for row in children_by_parent.get(None, [])) if node]


def get_context(context):
	selected_category = frappe.form_dict.get("category", "")
	top_rated = frappe.form_dict.get("top_rated") == "1"
	sort = frappe.form_dict.get("sort") if frappe.form_dict.get("sort") in SORT_OPTIONS else "alpha"
	# "Recommended" is on by default; only an explicit ?recommended=0 turns it off
	recommended_only = frappe.form_dict.get("recommended") != "0"
	is_logged_in = frappe.session.user != "Guest"

	# Resolve the tag before url() is defined: the closure binds selected_tag as
	# a default argument, so a later reassignment would not reach the links.
	approved_tags = get_approved_tag_names()
	selected_tag = frappe.form_dict.get("tag", "")
	if selected_tag not in approved_tags:
		# an unapproved or unknown tag is not a public filter
		selected_tag = ""

	def url(
		category=selected_category,
		top=top_rated,
		sort_by=sort,
		recommended=recommended_only,
		tag=selected_tag,
	):
		return build_url(category, top, sort_by, recommended, tag)

	# Everything except the category itself, so the taxonomy can count each
	# branch under the same rules the listing is about to apply.
	filters = {"published": 1}
	if recommended_only:
		filters["recommended"] = 1
	if top_rated:
		filters["average_rating"] = [">=", TOP_RATED_MINIMUM]

	if selected_tag:
		# Restrict by docname, since a tag lives in a child table rather than a
		# field this query can match on. An empty list matches nothing, which is
		# the right answer for a tag nothing carries.
		filters["name"] = [
			"in",
			frappe.get_all(
				"Resource Tag Link",
				filters={"tag": selected_tag, "parenttype": "Resource"},
				pluck="parent",
			),
		]

	path_pills = []
	option_pills = []

	# Categories a user has requested but an admin has not approved yet stay out
	# of the public tree, and so does anything filed under them. Resource blocks
	# publishing into a pending category, but a category can also be set back to
	# Pending long after its resources went live, so the listing has to filter on
	# the category's status rather than trust that check alone.
	approved_categories = get_approved_category_names()

	if selected_category:
		branch = [selected_category, *get_descendant_categories(selected_category)]
		filters["category"] = ["in", [name for name in branch if name in approved_categories]]

		path_pills = [
			{"name": name, "label": name, "url": url(category=name)}
			for name in get_category_path(selected_category)
		]

		children = frappe.get_all(
			"Category",
			filters={"parent_category": selected_category, "status": "Approved"},
			fields=["name", "category as label"],
			order_by="lft asc",
		)
		option_pills = [{"name": c.name, "label": c.label, "url": url(category=c.name)} for c in children]
	else:
		filters["category"] = ["in", sorted(approved_categories)]

		roots = frappe.get_all(
			"Category",
			filters={"parent_category": ["is", "not set"], "status": "Approved"},
			fields=["name", "category as label"],
			order_by="lft asc",
		)
		option_pills = [{"name": c.name, "label": c.label, "url": url(category=c.name)} for c in roots]

	# Counted before the category filter narrows anything, so every branch of the
	# taxonomy reports what it holds rather than only what the current category
	# selection left visible.
	branch_counts = Counter(
		frappe.get_all(
			"Resource",
			filters={**filters, "category": ["in", sorted(approved_categories)]},
			pluck="category",
		)
	)

	fields = [
		"name",
		"title",
		"route",
		"description",
		"category",
		"icon",
		"recommended",
		"average_rating",
		"rating_count",
		*CARD_FACT_FIELDS,
	]

	# Ties on the average go to the resource more people agreed on, so a lone
	# five star review does not outrank a well reviewed resource.
	order_by = "average_rating desc, rating_count desc, title asc" if sort == "rating" else "title asc"

	resources = frappe.get_all("Resource", filters=filters, fields=fields, order_by=order_by)

	tags_by_resource = get_tags_by_resource([r.name for r in resources], approved=approved_tags)

	for r in resources:
		r["tags"] = [{"name": t, "url": url(tag=t)} for t in tags_by_resource.get(r.name, [])]
		r["facts"] = build_card_facts(r)

	context.resources = resources
	context.category_tree = build_category_tree(branch_counts, url)
	context.category_tree_total = sum(branch_counts.values())
	context.path_pills = path_pills
	context.option_pills = option_pills
	context.selected_category = selected_category
	context.selected_tag = selected_tag
	context.clear_tag_url = url(tag="")
	context.top_rated = top_rated
	context.top_rated_minimum = TOP_RATED_MINIMUM
	context.recommended_only = recommended_only
	context.sort = sort
	context.sort_options = [
		{"value": key, "label": label, "url": url(sort_by=key)} for key, label in SORT_OPTIONS.items()
	]
	context.is_logged_in = is_logged_in
	context.all_url = url(category="", tag="")
	# What the closed controls display. A native select shows the selected
	# option's own text, so naming the control there would put "Filter:" on
	# every row of the open list too; these drive an overlay instead.
	context.sort_label = SORT_OPTIONS[sort]
	context.sort_tip = SORT_TIPS[sort]
	context.filter_options = [
		{
			"label": option["label"],
			"tip": option["tip"],
			"url": url(top=option["top_rated"], recommended=option["recommended"]),
			"selected": option["recommended"] == recommended_only
			and option["top_rated"] == top_rated,
		}
		for option in FILTER_OPTIONS
	]
	selected_filter = next(option for option in context.filter_options if option["selected"])
	context.filter_label = selected_filter["label"]
	context.filter_tip = selected_filter["tip"]
	context.empty_message = build_empty_message(selected_category, selected_tag, recommended_only, top_rated)
	context.no_breadcrumbs = True
	context.title = "Resources"
