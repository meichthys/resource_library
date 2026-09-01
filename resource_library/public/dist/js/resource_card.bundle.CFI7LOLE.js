(() => {
  // ../resource_library/resource_library/public/js/resource_card.bundle.js
  frappe.ready(function() {
    var gradients = [
      "linear-gradient(135deg, #7c3aed, #4f46e5)",
      "linear-gradient(135deg, #0d9488, #059669)",
      "linear-gradient(135deg, #db2777, #e11d48)",
      "linear-gradient(135deg, #ca8a04, #a16207)",
      "linear-gradient(135deg, #2563eb, #0891b2)",
      "linear-gradient(135deg, #ea580c, #dc2626)",
      "linear-gradient(135deg, #9333ea, #c026d3)",
      "linear-gradient(135deg, #64748b, #334155)"
    ];
    function hashGradient(name) {
      var h = Array.from(name || "").reduce(function(a, c) {
        return a + c.charCodeAt(0);
      }, 0);
      return gradients[h % gradients.length];
    }
    document.querySelectorAll(".card-cat").forEach(function(el) {
      el.style.background = hashGradient(el.dataset.category || el.textContent.trim());
    });
    document.querySelectorAll(".card-icon-placeholder").forEach(function(el) {
      var card = el.closest(".resource-card");
      el.style.background = hashGradient(card ? card.dataset.category : "");
    });
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
//# sourceMappingURL=resource_card.bundle.CFI7LOLE.js.map
