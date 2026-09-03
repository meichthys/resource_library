# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class License(Document):
	def validate(self):
		self.license_name = (self.license_name or "").strip()
		self.url = (self.url or "").strip()
