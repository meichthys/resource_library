// Copyright (c) 2026, Meichthys and contributors
// For license information, please see license.txt

frappe.listview_settings["Category"] = {
	onload(listview) {
		resource_library.add_approve_action(
			listview,
			__("categories"),
			__("They will be offered on the public site and shown in the category tree.")
		);
	},
};
