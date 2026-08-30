import frappe
from frappe.utils.password import update_password

EMAIL = "zz-list-tester@example.com"


def make():
	if not frappe.db.exists("User", EMAIL):
		frappe.get_doc({
			"doctype": "User", "email": EMAIL, "first_name": "ZZ",
			"send_welcome_email": 0, "roles": [],
		}).insert(ignore_permissions=True)
	update_password(EMAIL, "ZZtester!2345")
	for title, published in [("ZZ Listed A", 1), ("ZZ Listed B", 0)]:
		if not frappe.db.exists("Resource", {"title": title}):
			d = frappe.get_doc({
				"doctype": "Resource", "title": title, "description": "<p>x</p>",
				"category": "Books", "owner": EMAIL,
			}).insert(ignore_permissions=True)
			frappe.db.set_value("Resource", d.name, {"owner": EMAIL, "published": published})
	frappe.db.commit()


def drop():
	for title in ("ZZ Listed A", "ZZ Listed B"):
		name = frappe.db.get_value("Resource", {"title": title})
		if name:
			frappe.delete_doc("Resource", name, force=True)
	if frappe.db.exists("User", EMAIL):
		frappe.delete_doc("User", EMAIL, force=True)
	frappe.db.commit()
