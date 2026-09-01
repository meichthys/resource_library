from urllib.parse import quote

import frappe
from frappe.utils import pretty_date
from frappe.www.me import get_context as get_account_context

from resource_library.resource_library.doctype.resource_review.resource_review import MAX_RATING

no_cache = 1


def get_my_resources(user):
	"""Everything this person has submitted, whether or not it is published.

	Owner is what decides this, the same field "My Submissions" and the web
	form's edit permission key off, so a resource an admin filed on someone's
	behalf and then transferred shows up for the person it belongs to.
	"""
	resources = frappe.get_all(
		"Resource",
		filters={"owner": user},
		fields=[
			"name",
			"title",
			"route",
			"category",
			"published",
			"average_rating",
			"rating_count",
			"creation",
		],
		order_by="creation desc",
	)

	for resource in resources:
		resource["edit_url"] = f"/submit-resource/{quote(resource.name)}"
		resource["submitted_on"] = pretty_date(resource.creation)

	return resources


def get_my_reviews(user):
	"""Every review this person has left, including the ones still pending.

	A pending review is visible to nobody else, so this is the only place its
	author can see that it is still waiting rather than lost.
	"""
	reviews = frappe.get_all(
		"Resource Review",
		filters={"user": user},
		fields=["name", "resource", "rating", "review", "status", "modified"],
		order_by="modified desc",
	)

	if not reviews:
		return []

	resources = {
		r.name: r
		for r in frappe.get_all(
			"Resource",
			filters={"name": ["in", [review.resource for review in reviews]]},
			fields=["name", "title", "route", "published"],
		)
	}

	for review in reviews:
		resource = resources.get(review.resource)
		review["title"] = resource.title if resource else review.resource
		# Only published resources have a page to link to.
		review["route"] = resource.route if resource and resource.published else None
		review["updated_on"] = pretty_date(review.modified)

	return reviews


def get_context(context):
	"""The stock My Account page, plus what this site holds for the viewer.

	Frappe's /me is extended rather than replaced: it keeps the login check and
	owns the settings links, and its template is inherited so anything added to
	it upstream still turns up here.
	"""
	get_account_context(context)

	# /desk turns a Website User away outright (frappe.www.desk), and this site
	# has no portal menu, so frappe's own is_portal_user check never swaps that
	# link out. Hide it from anyone it would only bounce. Read from the user
	# record frappe's own context already loaded, rather than the session, which
	# does not always carry the type.
	context.can_access_desk = context.current_user.user_type != "Website User"
	context.max_rating = MAX_RATING
	context.my_resources = get_my_resources(frappe.session.user)
	context.my_reviews = get_my_reviews(frappe.session.user)
