/*
 * The Approve action the three moderated lists share (Category, Resource Tag
 * and Resource).
 *
 * What approving means differs per doctype and is decided server side in
 * approvals.py, so a list only has to say what it is holding: the noun for the
 * confirm, and a line saying what approving will do to the things selected.
 */
frappe.provide("resource_library");

resource_library.add_approve_action = function (listview, noun, effect) {
	/* Not offered to someone who cannot write the doctype at all. The real
	   check is the save on the server, which also has the permlevel the status
	   fields sit behind; this only keeps the menu honest. */
	if (!frappe.model.can_write(listview.doctype)) return;

	listview.page.add_actions_menu_item(
		__("Approve"),
		() => {
			const names = listview.get_checked_items(true);
			if (!names.length) return;

			frappe.confirm(
				__("Approve {0} selected {1}? {2}", [names.length, noun, effect]),
				() => resource_library.approve(listview, names, noun)
			);
		},
		false
	);
};

resource_library.approve = function (listview, names, noun) {
	frappe.call({
		method: "resource_library.approvals.approve",
		args: { doctype: listview.doctype, names: names },
		freeze: true,
		freeze_message: __("Approving..."),
	}).then((r) => {
		const result = r.message;
		if (!result) return;

		if (result.approved.length) {
			listview.clear_checked_items();
			listview.refresh();
		}

		/* Nothing to read when it all went through, so that case gets a toast
		   rather than a dialog to dismiss. Anything else is worth stopping for:
		   a refusal names the document and the reason it gave. */
		if (!result.skipped.length && !result.failed.length) {
			frappe.show_alert({
				message: __("Approved {0} {1}", [result.approved.length, noun]),
				indicator: "green",
			});
			return;
		}

		frappe.msgprint(
			resource_library.approval_summary(result, noun),
			__("Approval Summary"),
			true
		);
	});
};

resource_library.approval_summary = function (result, noun) {
	const lines = [];

	if (result.approved.length) {
		lines.push(`<p>${__("Approved {0} {1}.", [result.approved.length, noun])}</p>`);
	}

	if (result.skipped.length) {
		lines.push(
			`<p>${__("{0} were already approved.", [result.skipped.length])}</p>`
		);
	}

	if (result.failed.length) {
		const rows = result.failed
			.map(
				(f) =>
					`<li>${frappe.utils.escape_html(f.name)}: ${f.message}</li>`
			)
			.join("");
		lines.push(`<p>${__("Not approved:")}</p><ul>${rows}</ul>`);
	}

	return lines.join("");
};
