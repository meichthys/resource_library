// Copyright (c) 2026, Meichthys and contributors
// For license information, please see license.txt

frappe.listview_settings["Resource"] = {
	onload(listview) {
		// Approving a resource is publishing it, which is what `published`
		// holds; a resource whose category is still pending refuses, and says so
		// in the summary.
		resource_library.add_approve_action(
			listview,
			__("resources"),
			__("They will be published to the public site.")
		);
	},
};
