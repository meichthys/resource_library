import json
from urllib.parse import quote

import frappe
from frappe.utils.nestedset import get_descendants_of

no_cache = 1


def get_category_path(category):
	"""Root-to-leaf chain of category names ending in `category`.

	Walks parent_category links directly rather than lft/rgt (get_ancestors_of)
	— the nested-set boundaries on this site have repeatedly drifted out of
	sync after normal edits, while parent_category itself has stayed correct.
	"""
	path = []
	seen = set()
	while category and category not in seen:
		path.append(category)
		seen.add(category)
		category = frappe.db.get_value("Category", category, "parent_category")
	path.reverse()
	return path


SORT_OPTIONS = {
	"alpha": "Alphabetical",
	"likes": "Number of Likes",
}


def build_url(category, favorites_only, sort):
	params = []
	if category:
		params.append(f"category={quote(category)}")
	if favorites_only:
		params.append("favorites=1")
	if sort and sort != "alpha":
		params.append(f"sort={sort}")
	return "/resources" + ("?" + "&".join(params) if params else "")


def get_context(context):
	selected_category = frappe.form_dict.get("category", "")
	favorites_only = frappe.form_dict.get("favorites") == "1"
	sort = frappe.form_dict.get("sort") if frappe.form_dict.get("sort") in SORT_OPTIONS else "alpha"
	is_logged_in = frappe.session.user != "Guest"

	filters = {"published": 1}
	path_pills = []
	option_pills = []

	if selected_category:
		descendants = get_descendants_of("Category", selected_category, ignore_permissions=True)
		filters["category"] = ["in", [selected_category] + descendants]

		path_pills = [
			{"name": name, "label": name, "url": build_url(name, favorites_only, sort)}
			for name in get_category_path(selected_category)
		]

		children = frappe.get_all(
			"Category",
			filters={"parent_category": selected_category},
			fields=["name", "category as label"],
			order_by="lft asc",
		)
		option_pills = [
			{"name": c.name, "label": c.label, "url": build_url(c.name, favorites_only, sort)} for c in children
		]
	else:
		roots = frappe.get_all(
			"Category",
			filters={"parent_category": ["is", "not set"]},
			fields=["name", "category as label"],
			order_by="lft asc",
		)
		option_pills = [
			{"name": c.name, "label": c.label, "url": build_url(c.name, favorites_only, sort)} for c in roots
		]

	has_likes_column = frappe.db.has_column("Resource", "_liked_by")

	if favorites_only and is_logged_in and has_likes_column:
		filters["_liked_by"] = ["like", f'%"{frappe.session.user}"%']
	elif favorites_only and (not is_logged_in or not has_likes_column):
		# nobody has favorited anything yet, or viewer isn't logged in to have favorites
		filters["name"] = ["in", []]

	fields = ["name", "title", "route", "description", "category", "icon"]
	if has_likes_column:
		fields.append("_liked_by")

	resources = frappe.get_all("Resource", filters=filters, fields=fields, order_by="title asc")

	for r in resources:
		liked_by = json.loads(r.pop("_liked_by", None) or "[]")
		r["favorite_count"] = len(liked_by)
		r["is_favorited"] = is_logged_in and frappe.session.user in liked_by

	if sort == "likes":
		resources = sorted(resources, key=lambda r: (-r["favorite_count"], r["title"]))

	context.resources = resources
	context.path_pills = path_pills
	context.option_pills = option_pills
	context.selected_category = selected_category
	context.favorites_only = favorites_only
	context.sort = sort
	context.sort_options = [
		{"value": key, "label": label, "url": build_url(selected_category, favorites_only, key)}
		for key, label in SORT_OPTIONS.items()
	]
	context.is_logged_in = is_logged_in
	context.all_url = build_url("", favorites_only, sort)
	context.favorites_toggle_url = build_url(selected_category, not favorites_only, sort)
	context.no_breadcrumbs = True
	context.title = "Resources"
