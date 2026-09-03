# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

import frappe

# The Select options that named a real license, with the page its terms live on.
# Created approved: these are the vocabulary the site shipped with, not
# something a submitter asked for.
SHIPPED_LICENSES = {
	"Public Domain": "https://en.wikipedia.org/wiki/Public_domain",
	"CC0": "https://creativecommons.org/publicdomain/zero/1.0/",
	"CC BY": "https://creativecommons.org/licenses/by/4.0/",
	"CC BY-SA": "https://creativecommons.org/licenses/by-sa/4.0/",
	"CC BY-NC": "https://creativecommons.org/licenses/by-nc/4.0/",
	"CC BY-ND": "https://creativecommons.org/licenses/by-nd/4.0/",
	"MIT": "https://opensource.org/license/mit",
	"Apache-2.0": "https://www.apache.org/licenses/LICENSE-2.0",
	"GPL-2.0": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
	"GPL-3.0": "https://www.gnu.org/licenses/gpl-3.0.html",
}

# The rest of the Select options, which were buckets rather than licenses. A
# License names terms a reader can go and read, and none of these do: "Other
# open license" says only that the real one is somewhere else, "Free with
# conditions" that a site wrote its own terms, and "All rights reserved" that no
# license was granted at all. They are dropped rather than migrated, and any
# resource holding one is cleared, which the listing and the detail page already
# render as no license recorded.
BUCKET_LICENSES = (
	"Other open license",
	"Free with conditions",
	"All rights reserved",
)


def execute():
	"""Turn the license Select into records of the new License doctype.

	Every option that named a license becomes an approved License carrying the
	URL for its terms, so nothing a resource already records is lost. The column
	holds the license name either way and License is named by that same field,
	so the values on Resource carry across untouched and only their meaning
	changes: from free text to a link.

	Any name already in use that the shipped list does not cover is created too,
	so a site that customised the Select does not end up with resources pointing
	at a license that does not exist.
	"""
	for name, url in SHIPPED_LICENSES.items():
		if frappe.db.exists("License", name):
			continue

		frappe.get_doc(
			{"doctype": "License", "license_name": name, "url": url, "status": "Approved"}
		).insert(ignore_permissions=True)

	if not frappe.db.has_column("Resource", "license"):
		return

	resource = frappe.qb.DocType("Resource")

	# Cleared ahead of the scan below, so a bucket still in use is not mistaken
	# for a license the site added itself and recreated as one.
	frappe.qb.update(resource).set(resource.license, "").set(resource.license_input, "").set(
		resource.license_url_input, ""
	).where(resource.license.isin(BUCKET_LICENSES)).run()

	in_use = frappe.get_all(
		"Resource", filters={"license": ["is", "set"]}, pluck="license", distinct=True
	)
	for name in in_use:
		if name and not frappe.db.exists("License", name):
			frappe.get_doc(
				{"doctype": "License", "license_name": name, "status": "Approved"}
			).insert(ignore_permissions=True)

	# The plain text mirror the submission form writes to, backfilled so the
	# first save of an existing resource does not read it as a cleared license.
	frappe.qb.update(resource).set(resource.license_input, resource.license).where(
		resource.license.isnotnull() & (resource.license != "")
	).run()

	# A site that ran an earlier version of this patch has the buckets sitting in
	# the doctype. Nothing points at them any more, so drop them.
	for name in BUCKET_LICENSES:
		if frappe.db.exists("License", name):
			frappe.delete_doc("License", name, ignore_permissions=True)
