# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Carry App Store URL over to Download URL before the field is removed.

	The two said the same thing from different ends: one named the store a
	mobile app came from, the other where anything else could be fetched. A
	single Download URL covers both and applies to every category rather than
	only to software.

	Runs pre_model_sync, while app_store_url is still a field on the doctype.
	Only fills a Download URL that is empty, so a resource carrying both keeps
	the one an admin chose deliberately.
	"""
	if not frappe.db.has_column("Resource", "app_store_url"):
		return

	resource = frappe.qb.DocType("Resource")
	frappe.qb.update(resource).set(resource.download_url, resource.app_store_url).where(
		(resource.download_url.isnull() | (resource.download_url == ""))
		& resource.app_store_url.isnotnull()
		& (resource.app_store_url != "")
	).run()
