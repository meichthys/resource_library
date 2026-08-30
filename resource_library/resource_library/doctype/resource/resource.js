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
		warn_if_category_pending(frm);
		add_transfer_ownership_button(frm);
	},

	category(frm) {
		toggle_software_details(frm);
		warn_if_category_pending(frm);
	},

	published(frm) {
		warn_if_category_pending(frm);
	},
});

/**
 * Hand a resource over to the person it belongs to.
 *
 * A resource an admin filed on someone else's behalf is owned by the admin,
 * and the submission form gates editing on ownership, so the real owner cannot
 * touch their own listing until this moves. Custom buttons are cleared by
 * every refresh, so this re-adds itself rather than guarding against repeats.
 */
function add_transfer_ownership_button(frm) {
	if (frm.is_new() || !frappe.user.has_role("System Manager")) {
		return;
	}

	frm.add_custom_button(__("Transfer Ownership"), function () {
		frappe.prompt(
			[
				{
					fieldname: "current_owner",
					fieldtype: "Data",
					label: __("Current Owner"),
					default: frm.doc.owner,
					read_only: 1,
				},
				{
					fieldname: "user",
					fieldtype: "Link",
					options: "User",
					label: __("New Owner"),
					reqd: 1,
					description: __(
						"They will be able to edit this resource from the submission form, and the current owner will not."
					),
					// frappe.core.doctype.user.user.user_query drops Website Users
					// unless the caller opts out, and the people who submit
					// through the public form are exactly that: portal accounts
					// with no desk access. It already forces enabled = 1, but
					// Guest is a Website User too and has to stay out.
					get_query: () => ({ filters: { ignore_user_type: 1, name: ["!=", "Guest"] } }),
				},
			],
			function (values) {
				frappe.call({
					method: "resource_library.resource_library.doctype.resource.resource.transfer_ownership",
					args: { resource: frm.doc.name, user: values.user },
					freeze: true,
					freeze_message: __("Transferring ownership..."),
					callback(r) {
						if (!r.message) return;
						frappe.show_alert({
							message: __("Ownership transferred to {0}", [r.message]),
							indicator: "green",
						});
						frm.reload_doc();
					},
				});
			},
			__("Transfer Ownership"),
			__("Transfer")
		);
	});
}

/**
 * Banner when the resource's category is still awaiting approval.
 *
 * Nothing else on this form shows it: the category field looks perfectly
 * valid, and Published can already be ticked, yet the resource is kept off the
 * public listing because its category has not been approved. Links straight to
 * the category so it can be approved from here.
 */
function warn_if_category_pending(frm) {
	if (!frm.doc.category) {
		frm.set_intro();
		return;
	}

	frappe.call({
		method: "resource_library.resource_library.doctype.resource.resource.get_category_status",
		args: { category: frm.doc.category },
		callback(r) {
			// show_message appends rather than replaces, so clear first or a
			// second category change would stack a second banner underneath.
			frm.set_intro();

			if (r.message === "Approved") {
				return;
			}

			let label = frappe.utils.escape_html(frm.doc.category);
			let link = `<a href="/app/category/${encodeURIComponent(frm.doc.category)}">${label}</a>`;

			frm.set_intro(
				frm.doc.published
					? __(
							"Not showing on the site: category {0} is still pending approval. Approve the category to make this resource public.",
							[link]
						)
					: __(
							"Category {0} is still pending approval. This resource cannot be published until the category is approved.",
							[link]
						),
				"orange"
			);
		},
	});
}

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
