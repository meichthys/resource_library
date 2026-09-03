/*
 * Behaviour for the shared resource card (templates/includes/resource_card.html).
 * Loaded on every public page so the main listing and the Similar Resources
 * block on the detail page behave identically.
 */
frappe.ready(function () {
	/* Tag chips sit inside the card's <a>, so a nested link would be invalid
	   markup. Navigate manually and stop the card link from also firing. */
	document.querySelectorAll(".card-tag").forEach(function (el) {
		el.addEventListener("click", function (e) {
			e.preventDefault();
			e.stopPropagation();
			if (el.dataset.url) window.location.href = el.dataset.url;
		});
	});
});
