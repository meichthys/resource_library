# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

import json
import re
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint, get_url
from frappe.utils.nestedset import get_ancestors_of
from frappe.website.website_generator import WebsiteGenerator

from resource_library.badge import BADGE_SIZE

REPO_URL_PATTERN = re.compile(
	r"^https?://(?:www\.)?(github\.com|gitlab\.com)/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$"
)

# Resources anywhere in this branch of the tree are software, so they carry the
# repository and app store fields and must name a repository. The desk form and
# the public submission form both key their field visibility off this.
SOFTWARE_CATEGORY = "Software"


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
	return context


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
	be asked for as the parent of a new one; and `in_software`, so the form can
	show the software only fields without a round trip per category change.
	Pending categories are left out for the same reason pending tags are: a
	request from another user should not look like an established option.

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
				"in_software": int(SOFTWARE_CATEGORY in chain),
			}
		)

	options.sort(key=lambda option: option["label"])
	return options


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


class Resource(WebsiteGenerator):
	def validate(self):
		self.sync_category()
		if category_in_group(self.category, SOFTWARE_CATEGORY) and not self.source_code_repository:
			frappe.throw(_("Source Code Repository is required for Software resources"))
		self.sync_tags()
		self.validate_category_approved()

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

	def get_context(self, context):
		if self.category:
			ancestors = get_ancestors_of("Category", self.category)
			context.category_path = [*ancestors, self.category]
		else:
			context.category_path = []

		context.is_logged_in = frappe.session.user != "Guest"
		context.can_edit = context.is_logged_in and self.has_permission("write")
		context.edit_url = f"/submit-resource/{self.name}"
		context.badges = get_repo_badges(self.source_code_repository)
		context.recommended = self.recommended

		from_category = frappe.form_dict.get("from_category")
		context.back_url = f"/resources?category={quote(from_category)}" if from_category else "/resources"

		approved = self.get_approved_tags()
		context.tags = [
			{"name": tag, "url": f"/resources?tag={quote(tag)}&recommended=0"} for tag in approved
		]
		context.embed_variants = self.get_embed_variants()
		context.similar_resources = self.get_similar_resources(approved)

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
		fields = ["name", "title", "route", "description", "category", "icon", "recommended"]
		has_likes_column = frappe.db.has_column("Resource", "_liked_by")
		if has_likes_column:
			fields.append("_liked_by")

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

		is_logged_in = frappe.session.user != "Guest"
		tags_by_resource = get_tags_by_resource([r.name for r in matches])

		for r in matches:
			liked_by = json.loads(r.pop("_liked_by", None) or "[]")
			r["favorite_count"] = len(liked_by)
			r["is_favorited"] = is_logged_in and frappe.session.user in liked_by
			r["tags"] = [
				{"name": t, "url": f"/resources?tag={quote(t)}&recommended=0"}
				for t in tags_by_resource.get(r.name, [])
			]

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
