import frappe
from frappe import _


def get_context(context):
	"""Retitle the blank submission page.

	Frappe titles it "New {web form title}", which here reads as "New Submit a
	Resource". The web form's own title is already the breadcrumb above it, so
	this only has to name the thing being created.
	"""
	if frappe.form_dict.get("is_new"):
		context.title = _("New Resource")
