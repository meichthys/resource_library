# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

from frappe.utils.nestedset import NestedSet


class Category(NestedSet):
	nsm_parent_field = "parent_category"
