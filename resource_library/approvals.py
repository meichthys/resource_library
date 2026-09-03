# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

"""Approving in bulk from the desk lists.

Three doctypes carry the same editorial gate: something arrives from the public
site and stays out of sight until an admin says otherwise. Category and Resource
Tag hold that decision in `status`, Resource in `published`, so what approving
means is settled here rather than restated by each list's script.
"""

import frappe
from frappe import _
from frappe.utils import cint

# The lists that offer the action, and the field a decision lands in.
APPROVALS = {
	"Category": ("status", "Approved"),
	"Resource Tag": ("status", "Approved"),
	"Resource": ("published", 1),
}

# How many documents one call will take. Every one of them is a full save, so a
# large enough selection would run past the request timeout. Frappe's own bulk
# update hands anything over twenty to a background job for that reason; this
# stays in the request, where its summary can be the answer to the click, and
# caps the batch instead.
MAX_PER_CALL = 100


def is_approved(current, approved_value):
	"""Whether `current` already holds the approved value.

	`published` is a Check, which reaches here as 0/1, "0"/"1" or None
	depending on where it was set, so it is compared as a number rather than
	against the literal.
	"""
	if isinstance(approved_value, int):
		return cint(current) == approved_value

	return current == approved_value


@frappe.whitelist(methods=["POST"])
def approve(doctype, names):
	"""Approve `names`, reporting what happened to each one.

	Saved one at a time rather than updated in a single query: approving is
	exactly the moment a document's own validation has to run, since publishing
	a resource into a category nobody has approved yet is the thing that
	validation exists to stop. Each save sits in a savepoint, so a document that
	throws takes only itself back out and the rest of the batch still lands.

	Returns the names it approved, the ones that were already approved, and the
	ones that refused with the reason each gave.
	"""
	if doctype not in APPROVALS:
		frappe.throw(_("{0} has no approve action.").format(frappe.bold(doctype)))

	frappe.has_permission(doctype, "write", throw=True)

	if isinstance(names, str):
		names = frappe.parse_json(names)

	names = names or []
	if len(names) > MAX_PER_CALL:
		frappe.throw(
			_("Approve up to {0} at a time. {1} were selected.").format(MAX_PER_CALL, len(names))
		)

	fieldname, approved_value = APPROVALS[doctype]
	approved, skipped, failed = [], [], []

	for index, name in enumerate(names):
		doc = frappe.get_doc(doctype, name)
		if is_approved(doc.get(fieldname), approved_value):
			skipped.append(name)
			continue

		doc.set(fieldname, approved_value)

		save_point = f"rl_approve_{index}"
		frappe.db.savepoint(save_point)
		try:
			doc.save()
		except frappe.ValidationError as error:
			frappe.db.rollback(save_point=save_point)
			# The throw that got us here also queued itself for display. Left
			# alone, a batch of failures arrives as a modal each, in front of
			# the summary that is actually the answer to the click.
			frappe.clear_messages()
			failed.append({"name": name, "message": str(error)})
			continue

		frappe.db.release_savepoint(save_point)

		# A field the user cannot write at its permlevel is quietly put back
		# rather than refused, so a save can report success having changed
		# nothing. Read the value back rather than take the save's word for it.
		if is_approved(doc.get(fieldname), approved_value):
			approved.append(name)
		else:
			failed.append({"name": name, "message": _("You are not permitted to approve this.")})

	return {"approved": approved, "skipped": skipped, "failed": failed}
