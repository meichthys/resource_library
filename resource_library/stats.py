# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

import frappe

CACHE_KEY = "resource_library_footer_stats"
CACHE_TTL_SECONDS = 5 * 60


def get_library_stats():
	"""Public totals for the site footer.

	Counts only what a visitor can actually see: published resources, and
	reviews an admin has approved. Pending submissions and reviews are nobody
	else's business, so counting them here would advertise them.

	The footer renders on every page, so the numbers are cached briefly. They
	only move when someone submits something or an admin approves it, and a few
	minutes of lag on a page-bottom stat is not worth three counts per request.
	"""
	cached = frappe.cache.get_value(CACHE_KEY)
	if cached:
		return cached

	stats = {
		"resources": frappe.db.count("Resource", {"published": 1}),
		"recommended": frappe.db.count("Resource", {"published": 1, "recommended": 1}),
		"reviews": frappe.db.count("Resource Review", {"status": "Approved"}),
	}

	frappe.cache.set_value(CACHE_KEY, stats, expires_in_sec=CACHE_TTL_SECONDS)
	return stats
