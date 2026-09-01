# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, pretty_date

MAX_RATING = 5

# A review is one person's claim about a resource, so it waits for an admin the
# same way a user-suggested tag or category does. Only Approved reviews reach
# the public site or count towards a resource's average.
PENDING = "Pending"
APPROVED = "Approved"


def update_resource_rating(resource):
	"""Recompute a resource's stored average and review count.

	The average is stored on Resource rather than worked out per request so the
	listing can sort on it in the database, the way it used to sort on likes.

	Written with db.set_value rather than a save: nothing else about the
	resource is changing, and a save would re-run validation that can fail for
	reasons that have nothing to do with a review, such as a published resource
	whose category was set back to Pending after it went live.
	"""
	if not resource:
		return

	ratings = frappe.get_all(
		"Resource Review", filters={"resource": resource, "status": APPROVED}, pluck="rating"
	)

	count = len(ratings)
	average = round(sum(ratings) / count, 2) if count else 0

	frappe.db.set_value(
		"Resource",
		resource,
		{"average_rating": average, "rating_count": count},
		update_modified=False,
	)


def get_reviews(resource):
	"""Approved reviews for a resource, newest first, ready to render.

	The reviewer's display name is resolved in one query rather than per row,
	since a popular resource's page would otherwise make one round trip per
	review just to print a name.
	"""
	reviews = frappe.get_all(
		"Resource Review",
		filters={"resource": resource, "status": APPROVED},
		fields=["name", "user", "rating", "review", "creation"],
		order_by="creation desc",
	)

	if not reviews:
		return []

	full_names = dict(
		frappe.get_all(
			"User",
			filters={"name": ["in", list({r.user for r in reviews})]},
			fields=["name", "full_name"],
			as_list=True,
		)
	)

	for review in reviews:
		review["author"] = full_names.get(review.user) or _("Anonymous")
		review["posted_on"] = pretty_date(review.creation)

	return reviews


def get_user_review(resource, user=None):
	"""The viewer's own review of a resource, whatever its status.

	Returned regardless of approval so the form can show people what they wrote
	and tell them it is still waiting, rather than looking like it was lost.
	"""
	user = user or frappe.session.user
	if user == "Guest":
		return None

	name = frappe.db.get_value("Resource Review", {"resource": resource, "user": user})
	if not name:
		return None

	return frappe.db.get_value("Resource Review", name, ["rating", "review", "status"], as_dict=True)


@frappe.whitelist()
def submit_review(resource, rating, review):
	"""Record the viewer's review of a resource, or replace the one they left before.

	Runs with ignore_permissions because a reviewer is not given write access to
	the doctype: everything a review may contain is validated here, and status
	is not theirs to set, so the row is written on their behalf instead.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to leave a review."), frappe.PermissionError)

	published = frappe.db.get_value("Resource", resource, "published")
	if published is None:
		frappe.throw(_("Resource {0} does not exist.").format(frappe.bold(resource)))
	if not published:
		frappe.throw(_("This resource is not published yet, so it cannot be reviewed."))

	rating = cint(rating)
	if rating < 0 or rating > MAX_RATING:
		frappe.throw(_("Rating must be between 0 and {0} stars.").format(MAX_RATING))

	text = (review or "").strip()
	if not text:
		frappe.throw(_("Please write a few words about this resource."))

	name = frappe.db.get_value("Resource Review", {"resource": resource, "user": frappe.session.user})

	if name:
		doc = frappe.get_doc("Resource Review", name)
		doc.rating = rating
		doc.review = text
		# An edited review is a fresh claim about the resource, so it goes back
		# through approval instead of keeping the tick the old wording earned.
		doc.status = PENDING
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Resource Review",
				"resource": resource,
				"user": frappe.session.user,
				"rating": rating,
				"review": text,
				"status": PENDING,
			}
		).insert(ignore_permissions=True)

	return {"rating": doc.rating, "review": doc.review, "status": doc.status}


class ResourceReview(Document):
	def validate(self):
		self.validate_rating()
		self.validate_one_per_user()

	def validate_rating(self):
		self.rating = cint(self.rating)
		if self.rating < 0 or self.rating > MAX_RATING:
			frappe.throw(_("Rating must be between 0 and {0} stars.").format(MAX_RATING))

	def validate_one_per_user(self):
		"""One review per person per resource, so an average cannot be stacked.

		A unique index cannot express a pair of fields, and the public endpoint
		updates the row someone already has rather than adding a second one, so
		this catches the desk and anything else writing directly.
		"""
		duplicate = frappe.db.exists(
			"Resource Review",
			{"resource": self.resource, "user": self.user, "name": ["!=", self.name or ""]},
		)
		if duplicate:
			frappe.throw(_("{0} has already reviewed this resource.").format(frappe.bold(self.user)))

	def on_update(self):
		# Also runs on insert, and on the save that approves a pending review,
		# which is the point at which it starts counting.
		update_resource_rating(self.resource)

	def after_delete(self):
		update_resource_rating(self.resource)
