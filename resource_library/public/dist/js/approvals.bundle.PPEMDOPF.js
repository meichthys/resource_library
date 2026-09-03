(() => {
  // ../resource_library/resource_library/public/js/approvals.bundle.js
  frappe.provide("resource_library");
  resource_library.add_approve_action = function(listview, noun, effect) {
    if (!frappe.model.can_write(listview.doctype))
      return;
    listview.page.add_actions_menu_item(
      __("Approve"),
      () => {
        const names = listview.get_checked_items(true);
        if (!names.length)
          return;
        frappe.confirm(
          __("Approve {0} selected {1}? {2}", [names.length, noun, effect]),
          () => resource_library.approve(listview, names, noun)
        );
      },
      false
    );
  };
  resource_library.approve = function(listview, names, noun) {
    frappe.call({
      method: "resource_library.approvals.approve",
      args: { doctype: listview.doctype, names },
      freeze: true,
      freeze_message: __("Approving...")
    }).then((r) => {
      const result = r.message;
      if (!result)
        return;
      if (result.approved.length) {
        listview.clear_checked_items();
        listview.refresh();
      }
      if (!result.skipped.length && !result.failed.length) {
        frappe.show_alert({
          message: __("Approved {0} {1}", [result.approved.length, noun]),
          indicator: "green"
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
  resource_library.approval_summary = function(result, noun) {
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
      const rows = result.failed.map(
        (f) => `<li>${frappe.utils.escape_html(f.name)}: ${f.message}</li>`
      ).join("");
      lines.push(`<p>${__("Not approved:")}</p><ul>${rows}</ul>`);
    }
    return lines.join("");
  };
})();
//# sourceMappingURL=approvals.bundle.PPEMDOPF.js.map
