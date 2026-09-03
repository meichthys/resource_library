# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

import frappe

# Licensing and format details for the resources this site shipped with.
#
# Each value below was checked against the resource's own copyright or
# permissions page, not inferred from how freely it gives things away. Several
# of these ministries publish everything at no cost while explicitly forbidding
# redistribution, and would read as Public Domain to anyone going by feel.
# Bespoke permissions like those are not a license, so those resources are left
# out here entirely rather than filed under a catch-all: a blank says the site
# has no terms to point at, which is the truth of it.
#
# Counts are only set where the resource states one itself. Anything unknown is
# left out rather than estimated, since a card renders nothing for a blank.
SAMPLE_FIELDS = {
	"AndBible": {
		"license": "GPL-3.0",
	},
	"Berean Standard Bible": {
		"license": "CC0",
		"download_url": "https://berean.bible/downloads.htm",
	},
	"Bibledit": {
		"license": "GPL-3.0",
	},
	"Christian Classics Ethereal Library": {
		"license": "Public Domain",
		"download_url": "https://www.ccel.org/index/format",
	},
	"eBible.org": {
		"license": "Public Domain",
		"download_url": "https://ebible.org/download.php",
	},
	"Grace Gems": {
		"license": "Public Domain",
	},
	"Monergism": {
		# No license recorded: the underlying texts are largely public domain,
		# but Monergism's own editions are copyrighted and may not be
		# redistributed.
		"download_url": "https://www.monergism.com/blog/download-entire-monergism-ebook-library-1063-ebooks",
	},
	"Open English Bible": {
		"license": "CC0",
		"download_url": "https://openenglishbible.org/download/",
	},
	"unfoldingWord": {
		"license": "CC BY-SA",
		"download_url": "https://www.unfoldingword.org/for-translators/content",
	},
	"Xiphos": {
		"license": "GPL-2.0",
	},
}


# Nothing shipped with this site sits in the Music branch, so the music fields
# had no resource to appear on at all. The Open Hymnal Project is the natural
# first entry: public domain in all four parts, and it publishes editable ABC
# Plus source alongside the PDF and MIDI builds, which is exactly the difference
# between music you may play and music you may adapt that music_formats exists
# to record.
SAMPLE_MUSIC_RESOURCE = {
	"doctype": "Resource",
	"title": "Open Hymnal Project",
	"route": "open_hymnal_project",
	"description": (
		"<p>A freely distributable database of Christian hymns and spiritual songs, "
		"published as complete scores with all accompaniment parts. Every hymn ships "
		"as editable ABC Plus source alongside generated PDF and MIDI, so the "
		"arrangements can be transposed, re-set and rebuilt rather than only "
		"printed.</p>"
	),
	"category": "Music",
	"website": "http://openhymnal.org",
	"download_url": "http://openhymnal.org",
	"license": "Public Domain",
	"published": 1,
}


def add_sample_music_resource():
	"""Seed one Music resource, so the Music fields have somewhere to show.

	Left unrecommended: whether a resource is worth recommending is an editorial
	call for whoever runs the site, not something a patch should assert.
	"""
	if frappe.db.exists("Resource", {"title": SAMPLE_MUSIC_RESOURCE["title"]}):
		return

	if not frappe.db.exists("Category", "Music"):
		return

	frappe.get_doc(dict(SAMPLE_MUSIC_RESOURCE)).insert(ignore_permissions=True)


def execute():
	"""Fill in licensing, language and format details on the shipped resources.

	Only touches fields that are still empty, so an admin who has already
	recorded something keeps it. Written through the document rather than
	db.set_value so the category gating in Resource.validate applies: a book
	format set on a resource that is not in the Books branch gets cleared on the
	way in rather than sitting in a column nothing displays.
	"""
	for title, values in SAMPLE_FIELDS.items():
		name = frappe.db.get_value("Resource", {"title": title}, "name")
		if not name:
			continue

		doc = frappe.get_doc("Resource", name)
		changed = False

		for fieldname, value in values.items():
			if doc.get(fieldname):
				continue
			doc.set(fieldname, value)
			changed = True

		if changed:
			doc.save(ignore_permissions=True)

	add_sample_music_resource()
