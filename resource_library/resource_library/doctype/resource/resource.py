# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import get_ancestors_of
from frappe.website.website_generator import WebsiteGenerator


class Resource(WebsiteGenerator):
	def get_context(self, context):
		if self.category:
			ancestors = get_ancestors_of("Category", self.category)
			context.category_path = [*ancestors, self.category]
		else:
			context.category_path = []
