// Filter op de pagina "Schilderijen". Zonder JavaScript blijft gewoon alles zichtbaar.
(function () {
  var bar = document.querySelector('[data-filters]');
  var grid = document.querySelector('[data-gallery]');
  if (!bar || !grid) return;

  var items = Array.prototype.slice.call(grid.querySelectorAll('[data-item]'));
  var buttons = Array.prototype.slice.call(bar.querySelectorAll('[data-filter]'));
  var toggle = bar.querySelector('[data-toggle]');
  var empty = document.querySelector('[data-empty]');
  var category = 'all';
  var onlyForSale = false;

  function apply() {
    var shown = 0;
    items.forEach(function (el) {
      var ok = (category === 'all' || el.dataset.categorie === category) &&
               (!onlyForSale || el.dataset.status === 'Te koop');
      el.hidden = !ok;
      if (ok) shown++;
    });
    buttons.forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.filter === category));
    });
    if (toggle) toggle.setAttribute('aria-pressed', String(onlyForSale));
    if (empty) empty.hidden = shown !== 0;
  }

  buttons.forEach(function (b) {
    b.addEventListener('click', function () { category = b.dataset.filter; apply(); });
  });
  if (toggle) {
    toggle.addEventListener('click', function () { onlyForSale = !onlyForSale; apply(); });
  }

  bar.hidden = false;
})();
