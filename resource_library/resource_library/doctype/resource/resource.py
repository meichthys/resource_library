# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

import re
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint, get_url
from frappe.website.website_generator import WebsiteGenerator

from resource_library.badge import BADGE_SIZE
from resource_library.resource_library.doctype.resource_review.resource_review import (
	MAX_RATING,
	get_reviews,
	get_user_review,
)

REPO_URL_PATTERN = re.compile(
	r"^https?://(?:www\.)?(github\.com|gitlab\.com)/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$"
)

# Category branches that bring extra fields with them. A resource filed
# anywhere inside one of these branches carries that branch's fields, must fill
# in anything listed as required, and has every other branch's fields cleared on
# save. The desk form and the public submission form both drive their field
# visibility off this same map, so the three stay in step by construction.
CATEGORY_SECTIONS = {
	"Software": {
		"section": "software_details_section",
		"fields": ["source_code_repository", "app_store_url"],
		"required": ["source_code_repository"],
	},
	"Books": {
		"section": "book_details_section",
		"fields": ["book_formats", "title_count"],
		"required": [],
	},
	"Music": {
		"section": "music_details_section",
		"fields": ["music_formats", "music_styles", "track_count", "streaming_url"],
		"required": [],
	},
}

# Fixed vocabularies for the comma separated multi-value fields. These are
# developer-defined rather than records an admin curates, which is why they live
# here and not in a doctype: adding a format is a code change, not data entry.
BOOK_FORMATS = [
	"EPUB",
	"PDF",
	"MOBI/Kindle",
	"HTML",
	"Plain text",
	"Audiobook",
	"Source files",
]

MUSIC_FORMATS = [
	"Audio",
	"Sheet music",
	"Lead sheets",
	"Chord charts",
	"Lyrics",
	"MIDI",
	"Notation source",
	"Stems/multitracks",
	"Video",
]

MUSIC_STYLES = [
	"Hymns",
	"Contemporary worship",
	"Metrical psalms",
	"Gospel",
	"Choral",
	"Instrumental",
	"Children's",
	"Scripture songs",
]

# Fields whose value is a comma separated selection from a fixed list above.
# Anything not on the list is dropped on save, so a hand-typed value cannot
# quietly become a one-off format nobody else uses.
MULTI_VALUE_FIELDS = {
	"book_formats": BOOK_FORMATS,
	"music_formats": MUSIC_FORMATS,
	"music_styles": MUSIC_STYLES,
}

# Licenses that let someone adapt, translate and redistribute the work, which is
# the distinction this site exists to draw.
#
# The Creative Commons entries here are exactly the ones Creative Commons itself
# approves for Free Cultural Works: NC and ND are free of charge but not free of
# restriction, so they deliberately fall outside, and so does "Free with
# conditions", the bucket for a resource given away under its own bespoke terms.
# That last case turns out to be the common one among ministry websites, which
# routinely give everything away while forbidding redistribution.
OPEN_LICENSES = {
	"Public Domain",
	"CC0",
	"CC BY",
	"CC BY-SA",
	"MIT",
	"Apache-2.0",
	"GPL-2.0",
	"GPL-3.0",
	"Other open license",
}

# Formats named on a card before the rest roll up into a "+n" marker. The card
# already carries a banner, a rating, a category pill and a tag row, so this
# stays deliberately tight.
CARD_FORMAT_LIMIT = 3


def split_multi(raw):
	"""Comma separated field to a list, blanks and duplicates removed."""
	values = []
	seen = set()
	for part in (raw or "").split(","):
		label = part.strip()
		if label and label.lower() not in seen:
			seen.add(label.lower())
			values.append(label)
	return values


def is_open_license(license_name):
	return (license_name or "") in OPEN_LICENSES


# Fields a resource card needs beyond the listing's own, so the facts row can be
# built without a second query per card.
CARD_FACT_FIELDS = [
	"license",
	"book_formats",
	"music_formats",
	"title_count",
	"track_count",
]


def build_card_facts(row):
	"""The licence / formats / size line on a resource card.

	Returns None when the resource has none of it, so the template skips the
	markup rather than drawing an empty strip under the description.
	"""
	license_name = row.get("license")
	formats = split_multi(row.get("book_formats")) or split_multi(row.get("music_formats"))

	titles = cint(row.get("title_count"))
	tracks = cint(row.get("track_count"))
	count = titles or tracks

	if not (license_name or formats or count):
		return None

	count_label = ""
	if count:
		singular, plural = ("title", "titles") if titles else ("track", "tracks")
		count_label = f"{count:,} {singular if count == 1 else plural}"

	return {
		"license": license_name,
		"license_is_open": is_open_license(license_name),
		"formats": formats[:CARD_FORMAT_LIMIT],
		"formats_extra": max(len(formats) - CARD_FORMAT_LIMIT, 0),
		"count_label": count_label,
	}


def get_repo_badges(repo_url):
	"""Return shields.io badge configs for a GitHub/GitLab repo URL, or [] if unrecognized.

	Only GitHub and GitLab are supported. shields.io doesn't offer the
	license/stars/last-commit badge set for SourceForge, only download counts,
	so there's nothing meaningful to show for it here.
	"""
	if not repo_url:
		return []

	match = REPO_URL_PATTERN.match(repo_url.strip())
	if not match:
		return []

	host, owner, repo = match.groups()
	provider = "github" if host == "github.com" else "gitlab"
	slug = f"{owner}/{repo}"

	badges = [
		{"alt": "License", "src": f"https://img.shields.io/{provider}/license/{slug}"},
		{"alt": "Stars", "src": f"https://img.shields.io/{provider}/stars/{slug}"},
		{"alt": "Last Commit", "src": f"https://img.shields.io/{provider}/last-commit/{slug}"},
		{"alt": "Open Issues", "src": f"https://img.shields.io/{provider}/issues/{slug}"},
	]
	if provider == "github":
		badges.append({"alt": "Release", "src": f"https://img.shields.io/github/v/release/{slug}"})

	return badges


def get_list_context(context=None):
	"""Scope the web form's "My Submissions" list (/submit-resource/list) to the
	current user's own resources.

	Without this, frappe.www.list.get_list_data applies no owner filter at all,
	and since Resource has allow_guest_to_view=1 it also runs with
	ignore_permissions=True, so every logged-in user would see every other
	user's submissions, published or not, on their own "My Submissions" page.
	"""
	context = context or frappe._dict()
	context.filters = {"owner": frappe.session.user}
	context.no_breadcrumbs = True
	context.get_list = get_submission_list
	return context


def get_submission_list(**kwargs):
	"""Rows for "My Submissions".

	Two things the default listing gets wrong for a page whose whole job is to
	report back on what you submitted:

	frappe.www.list.prepare_filters pins is_published_field to 1 for any doctype
	that declares one, so a submitter could only ever see the submissions that
	had already been approved, never the ones still waiting. Owner scoping is
	what keeps this list private, so the published filter can go.

	And the Published column arrived as a raw 1, or as a blank cell for 0, since
	web_form_list.js formats a value it was given no fieldtype for and skips
	falsy ones entirely. Yes and No say the same thing and survive that.
	"""
	from frappe.www.list import get_list

	filters = dict(kwargs.pop("filters", None) or {})
	filters.pop("published", None)

	# Restored because frappe.www.list.get_list_data only passes it when the
	# module does not override get_list, and Resource does allow guest views.
	rows = get_list(filters=filters, ignore_permissions=True, **kwargs)

	for row in rows:
		if "published" in row:
			row["published"] = _("Yes") if row["published"] else _("No")

	return rows


def get_category_path(category):
	"""Root-to-leaf chain of category names ending in `category`.

	Walks parent_category links directly rather than lft/rgt (get_ancestors_of),
	since the nested-set boundaries on this site have repeatedly drifted out of
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


def get_descendant_categories(category):
	"""All descendants of `category`, walking parent_category links rather than
	lft/rgt (get_descendants_of). Same reasoning as get_category_path: the
	nested-set boundaries here have repeatedly drifted out of sync after normal
	edits, silently dropping resources filed under subcategories from results.
	"""
	children_by_parent = {}
	for row in frappe.get_all("Category", fields=["name", "parent_category"]):
		if row.parent_category:
			children_by_parent.setdefault(row.parent_category, []).append(row.name)

	descendants = []
	queue = list(children_by_parent.get(category, []))
	seen = set(queue)
	while queue:
		node = queue.pop()
		descendants.append(node)
		for child in children_by_parent.get(node, []):
			if child not in seen:
				seen.add(child)
				queue.append(child)
	return descendants


def get_approved_category_names():
	"""Every category an admin has approved. A category someone requested stays
	off the public site until then, and so does anything filed under it."""
	return set(frappe.get_all("Category", filters={"status": "Approved"}, pluck="name"))


def get_approved_tag_names():
	"""Every tag an admin has approved. User-suggested tags stay hidden from
	the public site until then."""
	return set(frappe.get_all("Resource Tag", filters={"status": "Approved"}, pluck="name"))


def get_tags_by_resource(resource_names, approved=None):
	"""Map of resource name to its ordered list of approved tags."""
	if not resource_names:
		return {}

	if approved is None:
		approved = get_approved_tag_names()

	rows = frappe.get_all(
		"Resource Tag Link",
		filters={"parent": ["in", resource_names], "parenttype": "Resource"},
		fields=["parent", "tag"],
		order_by="idx asc",
	)

	grouped = {}
	for row in rows:
		if row.tag in approved:
			grouped.setdefault(row.parent, []).append(row.tag)
	return grouped


@frappe.whitelist()
def get_category_options():
	"""Approved categories offered in the submission form's category pickers.

	Each option carries its full root-to-leaf path as the label, so a flat
	dropdown still reads as a tree; `is_group`, since only a group category can
	be asked for as the parent of a new one; and `branches`, the CATEGORY_SECTIONS
	keys this category sits under, so the form can show the right conditional
	fields without a round trip per category change. Pending categories are left
	out for the same reason pending tags are: a request from another user should
	not look like an established option.

	Ancestry comes from walking parent_category rather than ordering on
	lft/rgt, for the same reason get_category_path does: the nested-set
	boundaries on this site have repeatedly drifted out of sync after normal
	edits.
	"""
	rows = frappe.get_all(
		"Category", filters={"status": "Approved"}, fields=["name", "parent_category", "is_group"]
	)
	parents = {row.name: row.parent_category for row in rows}

	def ancestry(name):
		"""The category itself, then each parent above it, closest first."""
		chain = []
		seen = set()
		while name and name not in seen:
			chain.append(name)
			seen.add(name)
			name = parents.get(name)
		return chain

	options = []
	for row in rows:
		chain = ancestry(row.name)
		options.append(
			{
				"value": row.name,
				"label": " > ".join(reversed(chain)),
				"is_group": cint(row.is_group),
				"branches": [branch for branch in CATEGORY_SECTIONS if branch in chain],
			}
		)

	options.sort(key=lambda option: option["label"])
	return options


@frappe.whitelist()
def get_field_options():
	"""Vocabularies for the fixed multi-value pickers, plus the section map.

	Both forms build the same pill pickers and apply the same show/hide rule, so
	they read the shapes from here rather than each keeping their own copy that
	can drift out of step with the server that validates against it.
	"""
	return {
		"multi_value": MULTI_VALUE_FIELDS,
		"sections": CATEGORY_SECTIONS,
	}


def resolve_category_name(raw, parent=None, is_group=0):
	"""Map a typed category label to a Category docname.

	A label that does not exist yet is created without a status so the doctype
	default (Pending) applies, keeping user-requested categories off the public
	site, and off other submitters' pickers, until an admin approves them.

	A request can name a parent so the new category lands inside the existing
	tree instead of as another root, and say whether it should be able to hold
	subcategories of its own. The parent has to be an approved group: reshaping
	the approved tree, or hanging a request off a category that is itself only
	a request, is not something a public submission gets to do.
	"""
	label = (raw or "").strip()
	if not label:
		return None

	existing = frappe.db.get_value("Category", {"category": label}, "name")
	if existing:
		# Placement belongs to whoever approved the category. The parent and
		# group flag on a request only describe a category being created.
		return existing

	parent = (parent or "").strip()
	if parent:
		placement = frappe.db.get_value("Category", parent, ["status", "is_group"], as_dict=True)
		if not placement or placement.status != "Approved":
			frappe.throw(
				_("Parent category {0} is not available to file a new category under.").format(
					frappe.bold(parent)
				)
			)
		if not placement.is_group:
			frappe.throw(
				_("Parent category {0} is not a group, so it cannot contain subcategories.").format(
					frappe.bold(parent)
				)
			)

	category = frappe.get_doc(
		{
			"doctype": "Category",
			"category": label,
			"parent_category": parent or None,
			"is_group": cint(is_group),
		}
	)
	category.insert(ignore_permissions=True)
	return category.name


@frappe.whitelist()
def get_tag_options():
	"""Approved tag names offered in the submission form's tag picker.

	Pending tags are deliberately excluded: suggesting one is fine, but they
	should not look like established options to other submitters.
	"""
	return frappe.get_all(
		"Resource Tag", filters={"status": "Approved"}, order_by="tag_name asc", pluck="name"
	)


def resolve_tag_names(raw):
	"""Map comma separated text to Resource Tag docnames.

	Tags that do not exist yet are created without a status so the doctype
	default (Pending) applies, keeping user-suggested tags off the public site
	until an admin approves them.
	"""
	names = []
	seen = set()

	for part in (raw or "").split(","):
		label = part.strip()
		if not label or label.lower() in seen:
			continue
		seen.add(label.lower())

		existing = frappe.db.get_value("Resource Tag", {"tag_name": label}, "name")
		if existing:
			names.append(existing)
			continue

		tag = frappe.get_doc({"doctype": "Resource Tag", "tag_name": label})
		tag.insert(ignore_permissions=True)
		names.append(tag.name)

	return names


@frappe.whitelist()
def transfer_ownership(resource, user):
	"""Hand a resource over to the person it actually belongs to.

	The web form decides who may edit a submission by comparing the document's
	owner against the session user (WebForm.has_web_form_permission), and "My
	Submissions" is scoped the same way, so the owner field is the whole of what
	has to move for someone to take over a resource an admin filed for them.

	Written with db.set_value rather than a full save: nothing else about the
	document is changing, and a save would re-run validation that can fail for
	reasons that have nothing to do with the transfer, such as a published
	resource whose category was set back to Pending after it went live.
	"""
	frappe.only_for("System Manager")

	if not frappe.db.exists("Resource", resource):
		frappe.throw(_("Resource {0} does not exist").format(frappe.bold(resource)))

	if user == "Guest":
		frappe.throw(_("A resource cannot be owned by Guest."))

	target = frappe.db.get_value("User", user, ["enabled", "full_name"], as_dict=True)
	if not target:
		frappe.throw(_("User {0} does not exist").format(frappe.bold(user)))

	if not target.enabled:
		frappe.throw(_("User {0} is disabled and cannot own a resource.").format(frappe.bold(user)))

	previous = frappe.db.get_value("Resource", resource, "owner")
	if previous == user:
		frappe.throw(_("{0} already owns this resource.").format(frappe.bold(user)))

	frappe.db.set_value("Resource", resource, "owner", user)
	frappe.get_doc("Resource", resource).add_comment(
		"Info", _("Ownership transferred from {0} to {1}").format(previous, user)
	)

	return user


@frappe.whitelist()
def get_category_status(category):
	"""Approval status of a category, for the desk form's warning banner.

	A dedicated method rather than frappe.client.get_value from the client,
	because status sits at permlevel 1 on Category and reading it that way
	depends on the caller holding that level.
	"""
	return frappe.db.get_value("Category", category, "status")


@frappe.whitelist()
def category_in_group(category, group):
	"""Return True if `category` is `group` itself or a descendant of it in the Category tree.

	Walks the `parent_category` links directly rather than using lft/rgt ranges
	(get_ancestors_of), since the nested-set boundaries on this site have repeatedly
	drifted out of sync after normal edits, while parent_category itself has
	stayed correct, so this is the more reliable check for something that gates
	a mandatory-field validation.
	"""
	seen = set()
	while category and category not in seen:
		if category == group:
			return True
		seen.add(category)
		category = frappe.db.get_value("Category", category, "parent_category")
	return False


def get_category_branches(category):
	"""CATEGORY_SECTIONS keys whose branch contains `category`."""
	return [branch for branch in CATEGORY_SECTIONS if category_in_group(category, branch)]


@frappe.whitelist()
def get_category_sections(category):
	"""Which conditional sections a category turns on, for the desk form.

	One call rather than one per branch, and it keeps the branch names on the
	server: the form asks what to show, not whether a particular branch matched.
	"""
	return get_category_branches(category)


class Resource(WebsiteGenerator):
	def validate(self):
		self.sync_category()
		self.apply_category_sections()
		self.sync_tags()
		self.validate_category_approved()

	def apply_category_sections(self):
		"""Hold the conditional fields to the category they hang off.

		Fields belonging to a branch this resource is not in are cleared rather
		than left behind. A resource moved from Books to Software would
		otherwise keep a title count no form still shows, and it would surface
		again on the public card as though it meant something.
		"""
		branches = get_category_branches(self.category)

		applicable = set()
		for branch in branches:
			applicable.update(CATEGORY_SECTIONS[branch]["fields"])

		for spec in CATEGORY_SECTIONS.values():
			for fieldname in spec["fields"]:
				if fieldname in applicable:
					continue
				df = self.meta.get_field(fieldname)
				self.set(fieldname, 0 if df and df.fieldtype in ("Check", "Int") else None)

		self.normalize_multi_values()

		for branch in branches:
			for fieldname in CATEGORY_SECTIONS[branch]["required"]:
				if not self.get(fieldname):
					frappe.throw(
						_("{0} is required for {1} resources").format(
							_(self.meta.get_label(fieldname)), _(branch)
						)
					)

	def normalize_multi_values(self):
		"""Hold each comma separated selection to its fixed vocabulary.

		Anything off the list is dropped rather than kept, so a typo in the
		picker cannot become a one-off format that renders on a card and matches
		nothing else on the site.
		"""
		for fieldname, allowed in MULTI_VALUE_FIELDS.items():
			raw = self.get(fieldname)
			if not raw:
				continue
			lookup = {value.lower(): value for value in allowed}
			kept = [lookup[label.lower()] for label in split_multi(raw) if label.lower() in lookup]
			self.set(fieldname, ", ".join(kept))

	def sync_category(self):
		"""Keep the Category link and its plain text mirror in step.

		Web Forms validate Link fields against existing records, so the public
		submission form cannot be used to request a category that does not
		exist yet; it writes the plain text `category_input` instead, alongside
		the parent and group flag to file a new one with. Whichever side
		actually changed on this save wins: the desk edits the link, the web
		form edits the text field.
		"""
		previous_input = None
		if not self.is_new():
			previous_input = frappe.db.get_value("Resource", self.name, "category_input")

		if (self.category_input or "") != (previous_input or ""):
			resolved = resolve_category_name(
				self.category_input, self.category_parent_input, self.category_is_group_input
			)
			if resolved:
				self.category = resolved

		self.category_input = self.category or ""

		# The parent and group flag were only ever an instruction for creating a
		# category. Once one is resolved, hold them to where that category
		# actually sits, so they never linger as a request that was not honoured.
		placement = (
			frappe.db.get_value("Category", self.category, ["parent_category", "is_group"], as_dict=True)
			if self.category
			else None
		)
		self.category_parent_input = (placement and placement.parent_category) or ""
		self.category_is_group_input = cint(placement and placement.is_group)

	def validate_category_approved(self):
		"""Block publishing into a category an admin has not approved yet.

		Submitting under a requested category is fine, but publishing would put
		that category into the public tree, so the resource waits until the
		category itself is approved.
		"""
		if not self.published or not self.category:
			return

		if frappe.db.get_value("Category", self.category, "status") != "Approved":
			frappe.throw(
				_("Category {0} is pending approval, so this resource cannot be published yet.").format(
					frappe.bold(self.category)
				)
			)

	def sync_tags(self):
		"""Keep the Tags child table and its comma separated mirror in step.

		Web Forms cannot render a Table MultiSelect, so the public submission
		form writes the plain text `tags_input` instead. Whichever side actually
		changed on this save wins: the desk edits the child table, the web form
		edits the text field.
		"""
		previous_input = None
		if not self.is_new():
			previous_input = frappe.db.get_value("Resource", self.name, "tags_input")

		if (self.tags_input or "") != (previous_input or ""):
			self.set("tags", [])
			for tag_name in resolve_tag_names(self.tags_input):
				self.append("tags", {"tag": tag_name})

		self.tags_input = ", ".join(row.tag for row in (self.tags or []))

	def on_trash(self):
		"""Take this resource's reviews with it.

		A review holds a Link to the resource, so without this Frappe refuses to
		delete anything anyone has reviewed.
		"""
		super().on_trash()

		for name in frappe.get_all("Resource Review", filters={"resource": self.name}, pluck="name"):
			frappe.delete_doc("Resource Review", name, ignore_permissions=True, force=True)

	def get_context(self, context):
		# get_category_path rather than get_ancestors_of: the nested set
		# boundaries on this site have repeatedly drifted out of sync after
		# ordinary edits, and this breadcrumb is the whole of what tells a
		# visitor where in the tree they are.
		context.category_path = get_category_path(self.category) if self.category else []

		context.is_logged_in = frappe.session.user != "Guest"
		context.can_edit = context.is_logged_in and self.has_permission("write")
		context.edit_url = f"/submit-resource/{self.name}"
		context.badges = get_repo_badges(self.source_code_repository)
		context.recommended = self.recommended
		context.specs = self.get_detail_specs()
		context.license_is_open = is_open_license(self.license)

		from_category = frappe.form_dict.get("from_category")
		context.back_url = f"/resources?category={quote(from_category)}" if from_category else "/resources"

		approved = self.get_approved_tags()
		context.tags = [
			{"name": tag, "url": f"/resources?tag={quote(tag)}&recommended=0"} for tag in approved
		]
		context.embed_variants = self.get_embed_variants()
		context.similar_resources = self.get_similar_resources(approved)

		# The review form posts against the docname, which the template cannot
		# assume `name` still holds by the time the web context is built.
		context.resource_name = self.name
		context.max_rating = MAX_RATING
		context.average_rating = self.average_rating or 0
		context.rating_count = self.rating_count or 0
		context.reviews = get_reviews(self.name)
		# Shown back to its author whatever its status, so a review waiting for
		# approval does not look like it was thrown away.
		context.my_review = get_user_review(self.name)
		context.login_url = f"/login?redirect-to={quote('/' + (self.route or ''))}"

	def get_detail_specs(self):
		"""Label/value rows for the specification block on a listing page.

		Only what is actually filled in. A row carries either a single `value`,
		optionally linked, or a list of `values` the template draws as chips.
		Everything unset is left out rather than rendered blank, so a sparse
		resource shows a short block instead of a table of dashes.
		"""
		rows = []

		if self.license:
			rows.append(
				{
					"label": _("License"),
					"value": self.license,
					"url": self.license_url,
					"is_license": True,
				}
			)

		formats = split_multi(self.book_formats) or split_multi(self.music_formats)
		if formats:
			rows.append({"label": _("Formats"), "chips": formats})

		styles = split_multi(self.music_styles)
		if styles:
			rows.append({"label": _("Styles"), "chips": styles})

		languages = split_multi(self.languages)
		if languages:
			rows.append({"label": _("Languages"), "chips": languages})

		titles = cint(self.title_count)
		tracks = cint(self.track_count)
		if titles:
			rows.append({"label": _("Titles"), "value": f"{titles:,}"})
		elif tracks:
			rows.append({"label": _("Tracks"), "value": f"{tracks:,}"})

		return rows

	def get_approved_tags(self):
		"""This resource's tags that an admin has approved.

		User-suggested tags stay attached to the document but are not shown on
		the public site until approved.
		"""
		names = [row.tag for row in (self.tags or [])]
		if not names:
			return []

		approved = set(
			frappe.get_all(
				"Resource Tag", filters={"name": ["in", names], "status": "Approved"}, pluck="name"
			)
		)
		return [name for name in names if name in approved]

	def get_similar_resources(self, my_tags, limit=6):
		"""Published resources sharing tags or a nearby category with this one.

		Shared tags rank highest, since a tag is a deliberate curation signal.
		Categories are a tree, so an exact match ranks above merely sitting in
		the same branch; matching only on the exact category would find almost
		nothing once resources are filed into subcategories.
		"""
		scores = {}

		def add(name, weight):
			if name != self.name:
				scores[name] = scores.get(name, 0) + weight

		if my_tags:
			rows = frappe.get_all(
				"Resource Tag Link",
				filters={"tag": ["in", my_tags], "parenttype": "Resource", "parent": ["!=", self.name]},
				fields=["parent"],
			)
			for row in rows:
				add(row.parent, 3)

		if self.category:
			for name in frappe.get_all(
				"Resource",
				filters={"published": 1, "category": self.category, "name": ["!=", self.name]},
				pluck="name",
			):
				add(name, 2)

			# Siblings and children: the branch rooted at this category's parent,
			# falling back to its own subtree when it is already a root.
			parent = frappe.db.get_value("Category", self.category, "parent_category") or self.category
			branch = [parent, *get_descendant_categories(parent)]

			for name in frappe.get_all(
				"Resource",
				filters={"published": 1, "category": ["in", branch], "name": ["!=", self.name]},
				pluck="name",
			):
				add(name, 1)

		if not scores:
			return []

		# Re-query with published=1 so tag matches on unpublished drafts drop out,
		# and with the same approved-category rule the main listing applies, so a
		# category set back to Pending takes its resources out of here too.
		# Field list mirrors the main listing so the shared card macro renders.
		fields = [
			"name",
			"title",
			"route",
			"description",
			"category",
			"icon",
			"recommended",
			"average_rating",
			"rating_count",
			*CARD_FACT_FIELDS,
		]

		matches = frappe.get_all(
			"Resource",
			filters={
				"name": ["in", list(scores)],
				"published": 1,
				"category": ["in", sorted(get_approved_category_names())],
			},
			fields=fields,
		)
		matches.sort(key=lambda r: (-scores.get(r.name, 0), r.title))
		matches = matches[:limit]

		tags_by_resource = get_tags_by_resource([r.name for r in matches])

		for r in matches:
			r["tags"] = [
				{"name": t, "url": f"/resources?tag={quote(t)}&recommended=0"}
				for t in tags_by_resource.get(r.name, [])
			]
			r["facts"] = build_card_facts(r)

		return matches

	def get_embed_variants(self):
		"""Badge image URLs plus ready-to-paste embed snippets for this listing.

		Only recommended resources get an embeddable badge, since the badge
		asserts a recommendation. Returns [] otherwise so the template can skip
		the whole section.

		Uses absolute URLs throughout, since the snippet is meant to be pasted
		on someone else's site where relative paths would not resolve.
		"""
		if not self.recommended:
			return []

		site_url = get_url()
		listing_url = f"{site_url}/{self.route}"
		slug = quote(self.name, safe="")

		variants = []
		for key, label in (("dark", "Dark"), ("light", "Light")):
			badge_url = f"{site_url}/badge/{key}/{slug}.svg"
			snippet = (
				f'<a href="{listing_url}" target="_blank" rel="noopener">'
				f'<img src="{badge_url}" alt="{self.title} is recommended on Freely.Giving" '
				f'width="{BADGE_SIZE}" height="{BADGE_SIZE}">'
				f"</a>"
			)
			variants.append({"key": key, "label": label, "badge_url": badge_url, "code": snippet})

		return variants
