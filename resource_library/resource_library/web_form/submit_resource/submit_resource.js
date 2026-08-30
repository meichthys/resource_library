/**
 * Fields that only apply to software resources. The desk form keeps these in a
 * "Software Details" section it shows or hides as a unit (see resource.js);
 * Web Forms have no sections, so the same rule is applied field by field here.
 */
const SOFTWARE_FIELDS = ["source_code_repository", "app_store_url"];

frappe.ready(function () {
	if (in_view_mode()) {
		setup_view_mode();
		return;
	}

	setup_category_picker();
	setup_tag_picker();
});

/**
 * True on /submit-resource/<name>, the route Frappe treats as read: the same
 * form without a save button. /new and /<name>/edit are the writable ones.
 */
function in_view_mode() {
	return !!(frappe.web_form && frappe.web_form.in_view_mode);
}

/**
 * Frappe only drops the save button in view mode; every field underneath is
 * still a live input, so a viewer can pull a tag off, retype a category or
 * edit a URL and be left thinking it stuck. Mark the whole form read-only and
 * skip the pickers, which would otherwise put a fully interactive control
 * (removable pills, an open dropdown) on a page that cannot save.
 *
 * Read-only fields render their value as text, which is what a viewer wants
 * anyway: `tags_input` and `category_input` already carry the plain text
 * mirrors the pickers would have rebuilt.
 */
function setup_view_mode() {
	const web_form = frappe.web_form;
	if (!web_form || !web_form.fields_dict) return;

	// Frappe colours a plain read-only value with --disabled-text-color, but
	// controls that render their own markup instead of the plain display area
	// keep the inherited body colour, so values came out a mix of grey and
	// white. The stylesheet settles that off this class.
	$(".web-form").addClass("rl-view-mode");

	Object.keys(web_form.fields_dict).forEach(function (fieldname) {
		const field = web_form.fields_dict[fieldname];
		if (!field || !field.df) return;

		field.df.read_only = 1;
		field.refresh();
	});

	// How a category was requested is not part of the resource, and the
	// software only fields only apply when there is something in them.
	const doc = web_form.doc || {};
	const conditional = ["category_parent_input", "category_is_group_input"].concat(
		SOFTWARE_FIELDS.filter((fieldname) => !doc[fieldname])
	);

	conditional.forEach(function (fieldname) {
		const field = web_form.fields_dict[fieldname];
		if (field) field.toggle(false);
	});
}

/**
 * Both pickers warn that what was typed is a request an admin still has to
 * approve. One sentence that names the thing and says what becomes of it, on a
 * single wrapping line: the icon is inline, so wrapped lines start at the left
 * edge rather than indenting under the first word.
 *
 * `message` is translated copy with any typed values already escaped into it,
 * which is what bold_value is for.
 */
function render_pending_note($note, message) {
	if (!message) {
		$note.empty();
		return;
	}

	$note.html(`<span class="rl-tag-note-icon">!</span>${message}`);
}

function bold_value(value) {
	return `<strong>${frappe.utils.escape_html(value)}</strong>`;
}

/**
 * Web Forms validate Link fields against existing records, so the Category
 * link cannot be used to request a category that does not exist yet.
 * `category_input` is a plain Data field on the server instead; here we hide
 * that input and drive it with a searchable picker that also accepts a typed
 * name, keeping the underlying text in sync so the controller resolves it.
 *
 * A typed name is a request, so it also needs somewhere to go in the tree.
 * The parent and "can contain subcategories" fields exist for that, and are
 * only shown while the category being named is genuinely new.
 */
function setup_category_picker() {
	const web_form = frappe.web_form;
	if (!web_form || !web_form.fields_dict) return;

	const field = web_form.fields_dict.category_input;
	if (!field || !field.$wrapper) return;

	// Placement only applies to a new category, and the software only fields
	// only to a software one. Nothing is named yet, so keep both sets out of
	// the way rather than letting them flash in and back out while the approved
	// category list is still being fetched.
	["category_parent_input", "category_is_group_input", ...SOFTWARE_FIELDS].forEach(
		function (fieldname) {
			const conditional_field = web_form.fields_dict[fieldname];
			if (conditional_field) conditional_field.toggle(false);
		}
	);

	frappe.call({
		method: "resource_library.resource_library.doctype.resource.resource.get_category_options",
		callback: function (r) {
			build_category_picker(field, r.message || []);
		},
	});
}

/**
 * Replace a hidden Data field's input with an Autocomplete control.
 *
 * `ignore_validation` is what separates the two pickers built here: the
 * category picker keeps whatever is typed, because a name with no match is
 * exactly the request we want to capture, while the parent picker drops it,
 * because a parent has to be a category that already exists.
 */
function make_category_control(field, options, { placeholder, allow_new, on_change }) {
	const $input_wrapper = field.$wrapper.find(".control-input-wrapper");
	$input_wrapper.hide();

	const $host = $('<div class="rl-category-picker"></div>').insertAfter($input_wrapper);

	const control = frappe.ui.form.make_control({
		df: {
			fieldtype: "Autocomplete",
			fieldname: `rl_${field.df.fieldname}_picker`,
			placeholder: placeholder,
			ignore_validation: allow_new,
			options: options,
			change: function () {
				commit();
			},
		},
		parent: $host,
		render_input: true,
		only_input: true,
	});

	function commit() {
		const value = (control.get_value() || "").trim();

		// Write straight to the input rather than field.set_value(): set_value
		// calls set_input(), which re-renders the field and would destroy the
		// picker we injected into it.
		field.value = value;
		if (field.$input) field.$input.val(value);

		on_change(value);
	}

	control.$input.on("blur", function () {
		setTimeout(commit, 0);
	});

	control.$input.on("awesomplete-selectcomplete", function () {
		setTimeout(commit, 0);
	});

	return {
		control: control,
		commit: commit,
		clear: function () {
			control.set_value("");
			commit();
		},
		seed: function () {
			const initial = (field.get_value() || "").trim();
			if (initial) control.set_value(initial);
		},
	};
}

function build_category_picker(field, options) {
	const web_form = frappe.web_form;
	const approved_lookup = new Map(options.map((o) => [o.value.toLowerCase(), o]));
	const group_options = options.filter((o) => o.is_group);

	const parent_field = web_form.fields_dict.category_parent_input;
	const is_group_field = web_form.fields_dict.category_is_group_input;

	const $note = $('<div class="rl-tag-note"></div>').insertAfter(
		field.$wrapper.find(".control-input-wrapper")
	);

	let parent_picker = null;
	if (parent_field && parent_field.$wrapper) {
		parent_picker = make_category_control(parent_field, group_options, {
			placeholder: __("Top level, or search for a parent category"),
			allow_new: false,
			on_change: function () {
				const value = (field.get_value() || "").trim();
				toggle_software_details(value, !!value && !approved_lookup.has(value.toLowerCase()));
				render_note();
			},
		});
	}

	const category_picker = make_category_control(field, options, {
		placeholder: __("Search categories, or type a new one"),
		allow_new: true,
		on_change: function (value) {
			const is_new = !!value && !approved_lookup.has(value.toLowerCase());

			// Placement only describes a category being created. Clear it when
			// an existing one is chosen so a half-filled request from a moment
			// ago is not submitted alongside it.
			if (!is_new) {
				if (parent_picker) parent_picker.clear();
				if (is_group_field) is_group_field.set_value(0);
			}

			if (parent_field) parent_field.toggle(is_new);
			if (is_group_field) is_group_field.toggle(is_new);

			toggle_software_details(value, is_new);
			render_note();
		},
	});

	/**
	 * Show the software only fields when the chosen category sits anywhere in
	 * the Software branch, matching what the desk form does.
	 *
	 * A category being requested does not exist yet, so it has no branch of its
	 * own; it inherits the parent it is being filed under, which is also what
	 * the server sees once it has created the category and reaches the same
	 * check in Resource.validate.
	 */
	function toggle_software_details(value, is_new) {
		const parent = parent_field ? (parent_field.get_value() || "").trim() : "";
		const decides = is_new ? parent : value;
		const option = decides ? approved_lookup.get(decides.toLowerCase()) : null;
		const is_software = !!(option && option.in_software);

		// Mirrors the Software rule the server enforces in Resource.validate,
		// so the form reports it before a round trip rather than after.
		const repo_field = web_form.fields_dict.source_code_repository;
		if (repo_field) repo_field.df.reqd = is_software ? 1 : 0;

		SOFTWARE_FIELDS.forEach(function (fieldname) {
			const software_field = web_form.fields_dict[fieldname];
			if (software_field) software_field.toggle(is_software);
		});
	}

	function render_note() {
		const value = (field.get_value() || "").trim();

		if (!value || approved_lookup.has(value.toLowerCase())) {
			$note.empty();
			return;
		}

		const parent = parent_field ? (parent_field.get_value() || "").trim() : "";

		render_pending_note(
			$note,
			parent
				? __(
						"{0} is a new sub-category of {1}. Your resource will stay unpublished until an admin approves it.",
						[bold_value(value), bold_value(parent)]
					)
				: __(
						"{0} is a new top-level category. Your resource will stay unpublished until an admin approves it.",
						[bold_value(value)]
					)
		);
	}

	// Seed from an existing submission being edited
	if (parent_picker) parent_picker.seed();
	category_picker.seed();

	category_picker.commit();
}

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

		render_pending_note(
			$note,
			unapproved.length === 1
				? __("{0} is a new tag. It will appear publicly once an admin approves it.", [
						bold_value(unapproved[0]),
					])
				: __("{0} are new tags. They will appear publicly once an admin approves them.", [
						unapproved.map(bold_value).join(", "),
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
