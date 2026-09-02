# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

import frappe

from resource_library.resource_library.doctype.resource.resource import CATEGORY_SECTIONS


def execute():
	"""Create the category branches the conditional field sections key off.

	CATEGORY_SECTIONS gates the Book and Music fields on a resource sitting
	inside a category of that name. Sites installed before those sections
	existed have no Music root at all, so the fields could never be reached;
	Books is usually already there and is left exactly as an admin arranged it.

	Created approved rather than pending: these are part of the app, not a
	request from a submitter waiting on review.
	"""
	for name in CATEGORY_SECTIONS:
		if frappe.db.exists("Category", {"category": name}):
			continue

		frappe.get_doc(
			{
				"doctype": "Category",
				"category": name,
				"is_group": 1,
				"status": "Approved",
			}
		).insert(ignore_permissions=True)
