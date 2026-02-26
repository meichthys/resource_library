// Copyright (c) 2026, Meichthys and contributors
// For license information, please see license.txt

frappe.ui.form.on("Resource", {
	title(frm) {
		if (frm.is_new() && frm.doc.title) {
			let slug = frm.doc.title
				.toLowerCase()
				.trim()
				.replace(/[^a-z0-9\s_]/g, "")
				.replace(/\s+/g, "_");

			frm.set_value("route", slug);
		}
	},
});
