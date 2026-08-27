import frappe


def after_install():
	frappe.db.set_single_value("Website Settings", "disable_signup", 0)
