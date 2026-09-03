// Copyright (c) 2026, Meichthys and contributors
// For license information, please see license.txt

frappe.listview_settings["Resource Tag"] = {
	onload(listview) {
		resource_library.add_approve_action(
			listview,
			__("tags"),
			__("They will show on the cards that carry them and become public filters.")
		);
	},
};
