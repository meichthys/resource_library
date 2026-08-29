import json
from urllib.parse import quote

import frappe

from resource_library.resource_library.doctype.resource.resource import (
	get_approved_tag_names,
	get_category_path,
	get_descendant_categories,
	get_tags_by_resource,
)

no_cache = 1


SORT_OPTIONS = {
	"alpha": "Alphabetical",
	"likes": "Number of Likes",
}


def build_url(category, favorites_only, sort, recommended_only, tag):
	params = []
	if category:
		params.append(f"category={quote(category)}")
	if tag:
		params.append(f"tag={quote(tag)}")
	if favorites_only:
		params.append("favorites=1")
	if sort and sort != "alpha":
		params.append(f"sort={sort}")
	if not recommended_only:
		params.append("recommended=0")
	return "/resources" + ("?" + "&".join(params) if params else "")




def get_context(context):
	selected_category = frappe.form_dict.get("category", "")
	favorites_only = frappe.form_dict.get("favorites") == "1"
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
		favorites=favorites_only,
		sort_by=sort,
		recommended=recommended_only,
		tag=selected_tag,
	):
		return build_url(category, favorites, sort_by, recommended, tag)

	filters = {"published": 1}
	if recommended_only:
		filters["recommended"] = 1

	path_pills = []
	option_pills = []

	if selected_category:
		descendants = get_descendant_categories(selected_category)
		filters["category"] = ["in", [selected_category] + descendants]

		path_pills = [
			{"name": name, "label": name, "url": url(category=name)}
			for name in get_category_path(selected_category)
		]

		children = frappe.get_all(
			"Category",
			filters={"parent_category": selected_category},
			fields=["name", "category as label"],
			order_by="lft asc",
		)
		option_pills = [{"name": c.name, "label": c.label, "url": url(category=c.name)} for c in children]
	else:
		roots = frappe.get_all(
			"Category",
			filters={"parent_category": ["is", "not set"]},
			fields=["name", "category as label"],
			order_by="lft asc",
		)
		option_pills = [{"name": c.name, "label": c.label, "url": url(category=c.name)} for c in roots]

	has_likes_column = frappe.db.has_column("Resource", "_liked_by")

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

	if favorites_only and is_logged_in and has_likes_column:
		filters["_liked_by"] = ["like", f'%"{frappe.session.user}"%']
	elif favorites_only and (not is_logged_in or not has_likes_column):
		# nobody has favorited anything yet, or viewer isn't logged in to have favorites
		allowed_names = set()

	if allowed_names is not None:
		filters["name"] = ["in", list(allowed_names)]

	fields = ["name", "title", "route", "description", "category", "icon", "recommended"]
	if has_likes_column:
		fields.append("_liked_by")

	resources = frappe.get_all("Resource", filters=filters, fields=fields, order_by="title asc")

	tags_by_resource = get_tags_by_resource([r.name for r in resources], approved=approved_tags)

	for r in resources:
		liked_by = json.loads(r.pop("_liked_by", None) or "[]")
		r["favorite_count"] = len(liked_by)
		r["is_favorited"] = is_logged_in and frappe.session.user in liked_by
		r["tags"] = [{"name": t, "url": url(tag=t)} for t in tags_by_resource.get(r.name, [])]

	if sort == "likes":
		resources = sorted(resources, key=lambda r: (-r["favorite_count"], r["title"]))

	context.resources = resources
	context.path_pills = path_pills
	context.option_pills = option_pills
	context.selected_category = selected_category
	context.selected_tag = selected_tag
	context.clear_tag_url = url(tag="")
	context.favorites_only = favorites_only
	context.recommended_only = recommended_only
	context.sort = sort
	context.sort_options = [
		{"value": key, "label": label, "url": url(sort_by=key)} for key, label in SORT_OPTIONS.items()
	]
	context.is_logged_in = is_logged_in
	context.all_url = url(category="", tag="")
	context.favorites_toggle_url = url(favorites=not favorites_only)
	context.recommended_toggle_url = url(recommended=not recommended_only)
	context.no_breadcrumbs = True
	context.title = "Resources"
