# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Approve every category that predates the Category status field.

	The field defaults to Pending so user-requested categories start hidden,
	but categories already in the tree were curated by an admin. Without this
	they would all land on Pending, drop off the public listing, and block
	their resources from being published.

	Resources carry the plain text mirror of their category too, so backfill
	that here rather than waiting for each resource's next save.
	"""
	frappe.db.set_value(
		"Category", {"status": ["in", ["", None, "Pending"]]}, "status", "Approved", update_modified=False
	)

	resource = frappe.qb.DocType("Resource")
	frappe.qb.update(resource).set(resource.category_input, resource.category).where(
		(resource.category_input.isnull() | (resource.category_input == "")) & resource.category.isnotnull()
	).run()
