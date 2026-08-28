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

	refresh(frm) {
		toggle_software_details(frm);
	},

	category(frm) {
		toggle_software_details(frm);
	},
});

function toggle_software_details(frm) {
	if (!frm.doc.category) {
		frm.toggle_display("software_details_section", false);
		frm.toggle_reqd("source_code_repository", false);
		return;
	}

	frappe.call({
		method: "resource_library.resource_library.doctype.resource.resource.category_in_group",
		args: { category: frm.doc.category, group: "Software" },
		callback(r) {
			let is_software = !!r.message;
			frm.toggle_display("software_details_section", is_software);
			frm.toggle_reqd("source_code_repository", is_software);
		},
	});
}
