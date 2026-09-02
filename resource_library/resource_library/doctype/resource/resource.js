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
		setup_multi_pickers(frm);
		toggle_category_sections(frm);
		warn_if_category_pending(frm);
		add_transfer_ownership_button(frm);
	},

	category(frm) {
		toggle_category_sections(frm);
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

/**
 * Which conditional sections exist, what each contains, and the fixed
 * vocabularies behind the pill pickers.
 *
 * Fetched once and cached for the page: the shapes are code constants on the
 * server, so they cannot change between two calls in the same session, and both
 * the section toggle and the pickers need them on every refresh.
 */
let field_options = null;
let field_options_pending = [];

function with_field_options(callback) {
	if (field_options) {
		callback(field_options);
		return;
	}

	field_options_pending.push(callback);
	if (field_options_pending.length > 1) {
		// A request is already in flight; this callback rides along with it
		// rather than firing a second identical call on the same refresh.
		return;
	}

	frappe.call({
		method: "resource_library.resource_library.doctype.resource.resource.get_field_options",
		callback(r) {
			field_options = r.message || { multi_value: {}, sections: {} };
			let waiting = field_options_pending;
			field_options_pending = [];
			waiting.forEach((fn) => fn(field_options));
		},
	});
}

/**
 * Show the fields that belong to the branches this resource's category sits in,
 * and hide every other branch's.
 *
 * Both the sections and their required fields come from CATEGORY_SECTIONS on
 * the server, which is also what Resource.validate enforces and what clears the
 * fields of branches a resource is not in, so the form cannot drift away from
 * the rule it is previewing.
 */
function toggle_category_sections(frm) {
	with_field_options(function (options) {
		let sections = options.sections || {};

		function apply(active) {
			Object.keys(sections).forEach(function (branch) {
				let spec = sections[branch];
				let on = active.indexOf(branch) !== -1;

				frm.toggle_display(spec.section, on);
				(spec.fields || []).forEach((fieldname) => frm.toggle_display(fieldname, on));
				(spec.required || []).forEach((fieldname) => frm.toggle_reqd(fieldname, on));
			});
		}

		if (!frm.doc.category) {
			apply([]);
			return;
		}

		frappe.call({
			method: "resource_library.resource_library.doctype.resource.resource.get_category_sections",
			args: { category: frm.doc.category },
			callback(r) {
				apply(r.message || []);
			},
		});
	});
}

/**
 * Drive the comma separated multi-value fields with pill pickers.
 *
 * The values are a fixed vocabulary rather than records an admin curates, so
 * there is no doctype to hang a Table MultiSelect off, and the same comma
 * separated storage is what the public submission form has to write anyway.
 */
function setup_multi_pickers(frm) {
	with_field_options(function (options) {
		let vocabularies = options.multi_value || {};
		Object.keys(vocabularies).forEach(function (fieldname) {
			attach_pill_picker(frm, fieldname, vocabularies[fieldname]);
		});
	});
}

/**
 * The raw input is hidden through a stylesheet rather than jQuery, because a
 * control redraws itself whenever its value is set and would show the input
 * again halfway through editing.
 */
function ensure_picker_styles() {
	if (document.getElementById("rl-picker-styles")) {
		return;
	}

	let style = document.createElement("style");
	style.id = "rl-picker-styles";
	style.textContent =
		".rl-pill-driven > .control-input-wrapper { display: none !important; }" +
		".rl-pills .form-control { min-height: 0; }";
	document.head.appendChild(style);
}

function attach_pill_picker(frm, fieldname, choices) {
	let field = frm.get_field(fieldname);
	if (!field || !field.$wrapper) {
		return;
	}

	let current = split_values(frm.doc[fieldname]);

	// A picker built on an earlier refresh is still live, so re-seed it rather
	// than stacking a second control underneath the first. The DOM check
	// matters as well as the handle: a re-rendered form leaves the old control
	// object attached to a wrapper that is no longer on the page.
	if (field.rl_picker && field.$wrapper.find(".rl-pills").length) {
		field.rl_picker.set_value(current);
		return;
	}

	ensure_picker_styles();
	field.$wrapper.addClass("rl-pill-driven");

	// After the input it replaces, so the field's description stays underneath
	let $host = $('<div class="rl-pills"></div>').insertAfter(
		field.$wrapper.find(".control-input-wrapper")
	);

	let control = frappe.ui.form.make_control({
		df: {
			fieldtype: "MultiSelectPills",
			fieldname: `rl_${fieldname}_picker`,
			placeholder: __("Select one or more"),
			get_data: function () {
				return choices.map((choice) => ({ value: choice, label: choice }));
			},
			change: function () {
				commit();
			},
		},
		parent: $host,
		render_input: true,
		only_input: true,
	});

	function commit() {
		let rows = control.get_value();
		rows = Array.isArray(rows) ? rows.filter(Boolean) : [];
		frm.set_value(fieldname, rows.join(", "));
	}

	// Removing a pill mutates the control's rows directly, so re-read after the
	// click has settled rather than trusting the change event alone.
	$host.on("click", ".btn-remove", function () {
		setTimeout(commit, 0);
	});

	control.$input.on("awesomplete-selectcomplete", function () {
		setTimeout(commit, 0);
	});

	field.rl_picker = control;
	control.set_value(current);
}

function split_values(raw) {
	return String(raw || "")
		.split(",")
		.map((part) => part.trim())
		.filter(Boolean);
}
