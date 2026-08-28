# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

import re
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils.nestedset import get_ancestors_of
from frappe.website.website_generator import WebsiteGenerator

REPO_URL_PATTERN = re.compile(
	r"^https?://(?:www\.)?(github\.com|gitlab\.com)/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$"
)


def get_repo_badges(repo_url):
	"""Return shields.io badge configs for a GitHub/GitLab repo URL, or [] if unrecognized.

	Only GitHub and GitLab are supported — shields.io doesn't offer the
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
	ignore_permissions=True — so every logged-in user would see every other
	user's submissions, published or not, on their own "My Submissions" page.
	"""
	context = context or frappe._dict()
	context.filters = {"owner": frappe.session.user}
	context.no_breadcrumbs = True
	return context


@frappe.whitelist()
def category_in_group(category, group):
	"""Return True if `category` is `group` itself or a descendant of it in the Category tree.

	Walks the `parent_category` links directly rather than using lft/rgt ranges
	(get_ancestors_of) — the nested-set boundaries on this site have repeatedly
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
		if category_in_group(self.category, "Software") and not self.source_code_repository:
			frappe.throw(_("Source Code Repository is required for Software resources"))

	def get_context(self, context):
		if self.category:
			ancestors = get_ancestors_of("Category", self.category)
			context.category_path = [*ancestors, self.category]
		else:
			context.category_path = []

		context.can_edit = frappe.session.user != "Guest" and self.has_permission("write")
		context.edit_url = f"/submit-resource/{self.name}"
		context.badges = get_repo_badges(self.source_code_repository)

		from_category = frappe.form_dict.get("from_category")
		context.back_url = f"/resources?category={quote(from_category)}" if from_category else "/resources"
