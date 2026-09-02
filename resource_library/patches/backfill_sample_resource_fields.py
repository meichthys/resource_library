# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

import frappe

# Licensing and format details for the resources this site shipped with.
#
# Each value below was checked against the resource's own copyright or
# permissions page, not inferred from how freely it gives things away. That
# distinction matters more here than anywhere: several of these ministries
# publish everything at no cost while explicitly forbidding redistribution,
# which is "Free with conditions", not open. Monergism and Desiring God are both
# that case, and both would read as Public Domain to anyone going by feel.
#
# Counts are only set where the resource states one itself. Anything unknown is
# left out rather than estimated, since a card renders nothing for a blank.
SAMPLE_FIELDS = {
	"AndBible": {
		"license": "GPL-3.0",
		"license_url": "https://github.com/AndBible/and-bible/blob/master/LICENSE",
		"languages": "English, and Bible texts in hundreds of languages",
	},
	"Berean Standard Bible": {
		"license": "CC0",
		"license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
		"languages": "English",
		"download_url": "https://berean.bible/downloads.htm",
	},
	"Bible Gateway": {
		"license": "All rights reserved",
		"languages": "More than 70 languages",
	},
	"Bibledit": {
		"license": "GPL-3.0",
		"license_url": "https://github.com/bibledit/cloud/blob/master/COPYING",
		"languages": "English",
	},
	"Blue Letter Bible": {
		"license": "All rights reserved",
		"languages": "English",
	},
	"Christian Classics Ethereal Library": {
		"license": "Public Domain",
		"license_url": "https://www.ccel.org/copyright",
		"languages": "English, Latin, Greek",
		"download_url": "https://www.ccel.org/index/format",
		"book_formats": "EPUB, PDF, HTML, Plain text, MOBI/Kindle",
		# The count of ThML source files, which is one per work in the library
		"title_count": 1327,
	},
	"Desiring God": {
		# Free of charge, and freely quotable, but reproducing a whole work
		# needs written permission. See the permissions page.
		"license": "Free with conditions",
		"license_url": "https://www.desiringgod.org/permissions",
		"languages": "English, with selected translations",
		"book_formats": "EPUB, PDF, MOBI/Kindle",
	},
	"eBible.org": {
		"license": "Public Domain",
		"license_url": "https://ebible.org/publicdomain.htm",
		"languages": "More than 1,000 languages",
		"download_url": "https://ebible.org/download.php",
	},
	"Faith Comes By Hearing": {
		"license": "Free with conditions",
		"languages": "More than 1,000 languages",
	},
	"Free Bible Commentary": {
		# Redistribution is allowed, but only at no cost and with attribution,
		# which stops short of an open license.
		"license": "Free with conditions",
		"license_url": "https://www.freebiblecommentary.org/",
		"languages": "English, with translations in many languages",
	},
	"Grace Gems": {
		"license": "Public Domain",
		"languages": "English",
		"book_formats": "HTML, Plain text",
	},
	"Grace to You": {
		"license": "Free with conditions",
		"license_url": "https://www.gty.org/about#copyright",
		"languages": "English, Spanish",
	},
	"Monergism": {
		# The underlying texts are largely public domain, but Monergism's own
		# editions are copyrighted and may not be redistributed.
		"license": "Free with conditions",
		"license_url": "https://www.monergism.com/monergism-copyright-permissions",
		"languages": "English",
		"download_url": "https://www.monergism.com/blog/download-entire-monergism-ebook-library-1063-ebooks",
		"book_formats": "EPUB, PDF, MOBI/Kindle",
		"title_count": 1063,
	},
	"Open English Bible": {
		"license": "CC0",
		"license_url": "https://openenglishbible.org/blog/move-to-cc0/",
		"languages": "English",
		"download_url": "https://openenglishbible.org/download/",
	},
	"STEP Bible": {
		"license": "Other open license",
		"license_url": "https://github.com/STEPBible/STEPBible-Data",
		"languages": "More than 20 interface languages",
	},
	"unfoldingWord": {
		"license": "CC BY-SA",
		"license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
		"languages": "English, and gateway languages worldwide",
		"download_url": "https://www.unfoldingword.org/for-translators/content",
	},
	"Xiphos": {
		"license": "GPL-2.0",
		"license_url": "https://github.com/crosswire/xiphos/blob/master/COPYING",
		"languages": "English",
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
	"license_url": "http://openhymnal.org/copying.html",
	"languages": "English",
	"music_formats": "Sheet music, Notation source, MIDI, Lyrics",
	"music_styles": "Hymns",
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
