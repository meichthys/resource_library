frappe.ready(function () {
	setup_tag_picker();
});

/**
 * Web Forms cannot render a Table MultiSelect, so `tags_input` is a plain Data
 * field on the server. Here we hide that input and drive it with a searchable
 * pill picker, keeping the underlying comma separated value in sync so the
 * existing server side parsing keeps working unchanged.
 */
function setup_tag_picker() {
	const web_form = frappe.web_form;
	if (!web_form || !web_form.fields_dict) return;

	const field = web_form.fields_dict.tags_input;
	if (!field || !field.$wrapper) return;

	frappe.call({
		method: "resource_library.resource_library.doctype.resource.resource.get_tag_options",
		callback: function (r) {
			build_tag_picker(field, r.message || []);
		},
	});
}

function build_tag_picker(field, approved) {
	const approved_lookup = new Set(approved.map((t) => t.toLowerCase()));

	// Keep the label, hide the raw text input; it stays as the value carrier.
	const $input_wrapper = field.$wrapper.find(".control-input-wrapper");
	$input_wrapper.hide();

	const $host = $('<div class="rl-tag-picker"></div>').insertAfter($input_wrapper);
	const $note = $('<div class="rl-tag-note"></div>').insertAfter($host);

	const control = frappe.ui.form.make_control({
		df: {
			fieldtype: "MultiSelectPills",
			fieldname: "rl_tag_picker",
			placeholder: __("Search tags, or type a new one"),
			get_data: function () {
				return approved.map((t) => ({ value: t, label: t }));
			},
			change: function () {
				sync();
			},
		},
		parent: $host,
		render_input: true,
		only_input: true,
	});

	function current_rows() {
		const value = control.get_value();
		return Array.isArray(value) ? value.filter(Boolean) : [];
	}

	function sync() {
		const rows = current_rows();

		// Write straight to the input rather than field.set_value(): set_value
		// calls set_input(), which re-renders the field and would destroy the
		// picker we injected into it after the first tag was added.
		const text = rows.join(", ");
		field.value = text;
		if (field.$input) field.$input.val(text);

		const unapproved = rows.filter((t) => !approved_lookup.has(t.toLowerCase()));
		if (!unapproved.length) {
			$note.empty();
			return;
		}

		const names = unapproved.map((t) => frappe.utils.escape_html(t)).join(", ");
		$note.html(
			`<span class="rl-tag-note-icon">!</span>` +
				__("New tags are pending review. The new tags will appear publicly once they are approved by an admin:" +
					"<br><br>{0}. ", [
					`<strong>${names}</strong>`,
				])
		);
	}

	/**
	 * Turn whatever is typed into pills. Awesomplete only fires
	 * `selectcomplete` when an existing option is picked from the list, so a
	 * brand new tag would otherwise never be committed and would be discarded
	 * when the input lost focus.
	 */
	function commit_typed(raw) {
		const parts = String(raw || "")
			.split(",")
			.map((s) => s.trim())
			.filter(Boolean);

		if (!parts.length) return;

		const rows = current_rows();
		const seen = new Set(rows.map((r) => r.toLowerCase()));

		parts.forEach(function (part) {
			if (!seen.has(part.toLowerCase())) {
				seen.add(part.toLowerCase());
				rows.push(part);
			}
		});

		control.set_value(rows);
		control.$input.val("");
		sync();
	}

	control.$input.on("keydown", function (e) {
		// Comma always ends a tag
		if (e.key === "," || e.keyCode === 188) {
			e.preventDefault();
			commit_typed(control.$input.val());
			return;
		}

		// Enter ends a tag too, unless the dropdown has a highlighted option,
		// in which case Awesomplete should handle the selection itself.
		if (e.key === "Enter" || e.keyCode === 13) {
			const auto = control.awesomplete;
			const picking_from_list = auto && auto.opened && auto.index > -1;
			if (!picking_from_list && control.$input.val().trim()) {
				e.preventDefault();
				commit_typed(control.$input.val());
			}
		}
	});

	// Don't silently drop a half-typed tag when the field loses focus
	control.$input.on("blur", function () {
		if (control.$input.val().trim()) commit_typed(control.$input.val());
	});

	control.$input.on("paste", function (e) {
		const clipboard = (e.originalEvent || e).clipboardData;
		const text = clipboard && clipboard.getData("text");
		if (text && text.indexOf(",") !== -1) {
			e.preventDefault();
			commit_typed(control.$input.val() + text);
		}
	});

	// Picking an existing option goes through Awesomplete, not our handlers
	control.$input.on("awesomplete-selectcomplete", function () {
		setTimeout(sync, 0);
	});

	// Seed from an existing submission being edited
	const initial = (field.get_value() || "")
		.split(",")
		.map((s) => s.trim())
		.filter(Boolean);

	if (initial.length) {
		control.set_value(initial);
	}

	// Removing a pill mutates rows directly, so re-sync after the click settles
	$host.on("click", ".btn-remove", function () {
		setTimeout(sync, 0);
	});

	sync();
}
