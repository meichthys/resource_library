(() => {
  // ../resource_library/resource_library/public/js/resource_card.bundle.js
  frappe.ready(function() {
    document.querySelectorAll(".card-tag").forEach(function(el) {
      el.addEventListener("click", function(e) {
        e.preventDefault();
        e.stopPropagation();
        if (el.dataset.url)
          window.location.href = el.dataset.url;
      });
    });
  });
})();
//# sourceMappingURL=resource_card.bundle.QWSAC7Y5.js.map
