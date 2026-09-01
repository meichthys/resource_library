from urllib.parse import quote

import frappe

from resource_library.resource_library.doctype.resource.resource import (
	get_approved_category_names,
	get_approved_tag_names,
	get_category_path,
	get_descendant_categories,
	get_tags_by_resource,
)

no_cache = 1


SORT_OPTIONS = {
	"alpha": "Alphabetical",
	"rating": "Highest Rated",
}

# Stars a resource has to average before the Top Rated filter keeps it. An
# unrated resource averages 0, so it falls out of that filter on its own.
TOP_RATED_MINIMUM = 4


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

	filters = {"published": 1}
	if recommended_only:
		filters["recommended"] = 1

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

	if top_rated:
		filters["average_rating"] = [">=", TOP_RATED_MINIMUM]

	# Restrict by docname when a filter cannot be expressed as a plain field
	# match. None means unrestricted; an empty set means "match nothing".
	allowed_names = None

	if selected_tag:
		allowed_names = set(
			frappe.get_all(
				"Resource Tag Link",
				filters={"tag": selected_tag, "parenttype": "Resource"},
				pluck="parent",
			)
		)

	if allowed_names is not None:
		filters["name"] = ["in", list(allowed_names)]

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
	]

	# Ties on the average go to the resource more people agreed on, so a lone
	# five star review does not outrank a well reviewed resource.
	order_by = (
		"average_rating desc, rating_count desc, title asc" if sort == "rating" else "title asc"
	)

	resources = frappe.get_all("Resource", filters=filters, fields=fields, order_by=order_by)

	tags_by_resource = get_tags_by_resource([r.name for r in resources], approved=approved_tags)

	for r in resources:
		r["tags"] = [{"name": t, "url": url(tag=t)} for t in tags_by_resource.get(r.name, [])]

	context.resources = resources
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
	context.top_rated_toggle_url = url(top=not top_rated)
	context.recommended_toggle_url = url(recommended=not recommended_only)
	context.empty_message = build_empty_message(
		selected_category, selected_tag, recommended_only, top_rated
	)
	context.no_breadcrumbs = True
	context.title = "Resources"
