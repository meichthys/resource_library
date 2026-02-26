import frappe
from frappe.utils.nestedset import get_descendants_of

no_cache = 1


def get_context(context):
	selected_category = frappe.form_dict.get("category", "")

	filters = {"published": 1}
	if selected_category:
		descendants = get_descendants_of("Category", selected_category)
		filters["category"] = ["in", [selected_category] + descendants]

	resources = frappe.get_all(
		"Resource",
		filters=filters,
		fields=["name", "title", "route", "description", "category", "icon"],
		order_by="title asc",
	)

	categories = frappe.get_all(
		"Category",
		fields=["name", "category as label", "parent_category"],
		order_by="lft asc",
	)

	context.resources = resources
	context.categories = categories
	context.selected_category = selected_category
	context.no_breadcrumbs = True
	context.title = "Resources"
