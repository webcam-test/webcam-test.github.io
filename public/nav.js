// Shared header/footer navigation behaviour for every page (tool pages, info
// pages, and 404) — identical across all three templates, so it lives here
// once instead of being duplicated verbatim in each <script> block. The
// DOMContentLoaded block at the bottom starts everything; each init function
// is a no-op on pages without its markup.
function initCategoryDropdowns() {
  var buttons = document.querySelectorAll('.cat-menu-btn');
  function closeAll(except) {
    buttons.forEach(function (b) {
      if (b === except) return;
      b.setAttribute('aria-expanded', 'false');
      var menu = document.getElementById(b.getAttribute('aria-controls'));
      if (menu) menu.classList.remove('open');
    });
  }
  function positionMenu(b, menu) {
    var rect = b.getBoundingClientRect();
    menu.style.top = (rect.bottom + 8) + 'px';
    menu.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - menu.offsetWidth - 8)) + 'px';
  }
  buttons.forEach(function (b) {
    b.addEventListener('click', function (e) {
      e.stopPropagation();
      var expanded = b.getAttribute('aria-expanded') === 'true';
      closeAll();
      var menu = document.getElementById(b.getAttribute('aria-controls'));
      if (!expanded && menu) {
        menu.classList.add('open');
        positionMenu(b, menu);
        b.setAttribute('aria-expanded', 'true');
      }
    });
  });
  document.addEventListener('click', function () { closeAll(); });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    // Focus inside a menu that's about to be hidden would be lost, so hand
    // it back to that menu's own button first.
    var openMenu = document.activeElement && document.activeElement.closest('.tools-menu.open');
    closeAll();
    if (openMenu) {
      var owner = document.querySelector('[aria-controls="' + openMenu.id + '"]');
      if (owner) owner.focus();
    }
  });
  // .tools-menu is position:fixed, positioned once (via getBoundingClientRect())
  // at click time -- it doesn't track the button on scroll, and the header
  // isn't sticky, so without this the open menu stays glued to its original
  // spot on screen while the button scrolls away underneath it. Closing on
  // scroll is simpler and cheaper than repositioning on every scroll event.
  window.addEventListener('scroll', function () { closeAll(); }, { passive: true });
  return closeAll;
}
// Below the 860px hamburger breakpoint (styles.css), .category-strip
// itself is display:none, so this collapse-into-"More" math never
// actually gets a chance to show "More" in practice at today's item
// count/label lengths (there's headroom above 860px). Left in place as
// a defensive fallback for a future longer SITE_NAME or an added nav
// group, not dead code to remove.
// The "More" dropdown's sections are copies of the category menus (same
// icon, label and links), so they're cloned from those menus here rather
// than shipped as a second copy of every link in each page's HTML.
function buildMoreMenu() {
  var panel = document.getElementById('moreMenuPanel');
  if (!panel || panel.children.length) return;
  document.querySelectorAll('.category-strip .cat-menu-item[data-cat-key]').forEach(function (item) {
    var menu = item.querySelector('.cat-menu');
    if (!menu) return;
    var section = document.createElement('div');
    section.className = 'more-menu-section';
    section.setAttribute('data-cat-key', item.getAttribute('data-cat-key'));
    var heading = document.createElement('div');
    heading.className = 'more-menu-heading';
    var icon = document.createElement('span');
    icon.className = 'more-menu-icon';
    var svg = menu.querySelector('.menu-panel-icon svg');
    if (svg) icon.appendChild(svg.cloneNode(true));
    heading.appendChild(icon);
    var label = menu.querySelector('.menu-panel-header strong');
    heading.appendChild(document.createTextNode(label ? label.textContent : ''));
    section.appendChild(heading);
    menu.querySelectorAll('.menu-panel-links a').forEach(function (a) { section.appendChild(a.cloneNode(true)); });
    panel.appendChild(section);
  });
}
function initPriorityNav(closeAll) {
  // Priority+ pattern: every .cat-menu-item[data-cat-key] in .category-strip
  // (rendered by render_category_dropdowns() in generate.py) is a candidate
  // to hide; whichever ones don't fit this viewport's width get display:none
  // and their matching .more-menu-section (rendered by render_more_menu(),
  // same data-cat-key) is revealed inside the trailing "More" dropdown
  // instead. Runs identically at every width (mobile included, now that the
  // strip shares .top-nav's row with the logo) rather than branching on a
  // breakpoint — replaced an earlier horizontal-scroll version of this same
  // strip, which had no affordance signaling there was more content
  // off-screen.
  var strip = document.querySelector('.category-strip');
  var moreItem = document.getElementById('moreMenuItem');
  if (!strip || !moreItem) return;
  var items = Array.prototype.slice.call(strip.querySelectorAll('.cat-menu-item[data-cat-key]'));
  var sections = document.querySelectorAll('.more-menu-section');
  function layout() {
    items.forEach(function (item) { item.style.removeProperty('display'); });
    sections.forEach(function (s) { s.classList.remove('cat-visible'); });
    moreItem.style.display = 'flex';

    var available = strip.clientWidth;
    var gap = parseFloat(getComputedStyle(strip).columnGap) || 0;
    var fixedWidth = 0;
    Array.prototype.forEach.call(strip.children, function (el) {
      if (el !== moreItem && items.indexOf(el) === -1) {
        fixedWidth += el.getBoundingClientRect().width + gap;
      }
    });
    var moreWidth = moreItem.getBoundingClientRect().width + gap;
    var itemWidths = items.map(function (it) { return it.getBoundingClientRect().width + gap; });
    var total = itemWidths.reduce(function (a, b) { return a + b; }, fixedWidth);

    if (total <= available) {
      moreItem.style.display = 'none';
      return;
    }

    var used = fixedWidth;
    var visibleCount = 0;
    for (var i = 0; i < itemWidths.length; i++) {
      if (used + itemWidths[i] + moreWidth > available) break;
      used += itemWidths[i];
      visibleCount++;
    }

    items.forEach(function (item, idx) {
      if (idx >= visibleCount) {
        item.style.display = 'none';
        var section = document.querySelector('.more-menu-section[data-cat-key="' + item.getAttribute('data-cat-key') + '"]');
        if (section) section.classList.add('cat-visible');
      }
    });
  }
  var resizeTimer;
  window.addEventListener('resize', function () {
    closeAll();
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(layout, 100);
  });
  layout();
  // Safety re-run once every stylesheet has actually applied (styles.min.css
  // loads via the preload+swap trick in <head>, so at DOMContentLoaded time
  // — especially in the --no-minify dev build, which ships no critical CSS
  // — .category-strip's flex layout may not be active yet, making the
  // measurement above see unstyled (full-width) items and over-collapse
  // into "More". layout() is idempotent, so re-running it here just
  // self-corrects once real widths are available.
  window.addEventListener('load', layout);
  // Second, separate safety re-run: DM Sans loads via font-display:swap, so
  // on a genuine first visit (nothing cached yet) the very first layout()
  // call above measures each button's width using the metrics-matched
  // fallback font, not the real one -- and window's own 'load' event does
  // NOT wait for that font swap (font-display:swap is deliberately
  // non-render-blocking), so the 'load' re-run above can still be measuring
  // the fallback font too. Without this, the strip only ever gets the
  // correct item count after something else happens to trigger a resize
  // (e.g. a manual reload, where the font is already warm). document.fonts
  // .ready resolves once the real font has actually swapped in, so this is
  // the one re-run that's guaranteed to see final metrics.
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(layout);
  }
}
function initMobileDrawer() {
  var hamburger = document.getElementById('navHamburgerBtn');
  var drawer = document.getElementById('navDrawer');
  var backdrop = document.getElementById('navDrawerBackdrop');
  var closeBtn = document.getElementById('navDrawerClose');
  if (!hamburger || !drawer || !backdrop) return;
  var sectionButtons = drawer.querySelectorAll('.drawer-section-btn');
  function isOpen() { return drawer.classList.contains('open'); }
  function openDrawer() {
    drawer.hidden = false;
    backdrop.hidden = false;
    setTimeout(function () {
      drawer.classList.add('open');
      backdrop.classList.add('open');
    }, 10);
    hamburger.setAttribute('aria-expanded', 'true');
    document.body.classList.add('drawer-open');
    // The drawer is an aria-modal dialog, so focus moves into it.
    closeBtn.focus();
  }
  function closeDrawer(returnFocus) {
    var hadFocus = drawer.contains(document.activeElement);
    drawer.classList.remove('open');
    backdrop.classList.remove('open');
    hamburger.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('drawer-open');
    if (returnFocus !== false && hadFocus) hamburger.focus();
    setTimeout(function () {
      if (!isOpen()) { drawer.hidden = true; backdrop.hidden = true; }
    }, 220);
  }
  hamburger.addEventListener('click', function () { isOpen() ? closeDrawer() : openDrawer(); });
  closeBtn.addEventListener('click', function () { closeDrawer(); });
  backdrop.addEventListener('click', function () { closeDrawer(); });
  document.addEventListener('keydown', function (e) {
    if (!isOpen()) return;
    if (e.key === 'Escape') { closeDrawer(); return; }
    if (e.key !== 'Tab') return;
    // Keep Tab inside the open dialog: wrap from the last visible control
    // back to the first (and the reverse for Shift+Tab).
    var focusable = Array.prototype.filter.call(
      drawer.querySelectorAll('a[href], button'),
      function (el) { return el.getClientRects().length > 0; }
    );
    if (!focusable.length) return;
    var first = focusable[0], last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });
  sectionButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var expanded = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      var panel = document.getElementById(btn.getAttribute('aria-controls'));
      if (panel) panel.classList.toggle('open', !expanded);
    });
  });
  var mq = window.matchMedia('(min-width:861px)');
  var mqHandler = function (e) { if (e.matches && isOpen()) closeDrawer(false); };
  if (mq.addEventListener) mq.addEventListener('change', mqHandler);
  else mq.addListener(mqHandler);
}
function wrapTables() {
  document.querySelectorAll('.article table').forEach(function (table) {
    if (table.closest('.table-scroll')) return;
    var wrap = document.createElement('div');
    wrap.className = 'table-scroll';
    table.parentNode.insertBefore(wrap, table);
    wrap.appendChild(table);
  });
}
function initToolForm() {
  // .tool-grid is a real <form> so labelled inputs get proper native
  // association, but every action on the page is its own type="button"
  // handled by that tool's own script — this only exists to stop a lone
  // qualifying text input from triggering the browser's own implicit
  // form submission on Enter (which would navigate/reload and drop all
  // in-memory camera/audio state).
  var form = document.querySelector('form.tool-grid');
  if (!form) return;
  form.addEventListener('submit', function (e) { e.preventDefault(); });
}
function renderMath() {
  // KaTeX (katex.min.js + auto-render) is only loaded on pages whose article
  // contains LaTeX; those scripts are deferred ahead of this file, so they
  // have already run by the time this does.
  if (!window.renderMathInElement) return;
  renderMathInElement(document.querySelector('main') || document.body, {
    delimiters: [
      { left: '$$', right: '$$', display: true },
      { left: '\\[', right: '\\]', display: true },
      { left: '\\(', right: '\\)', display: false }
    ],
    throwOnError: false
  });
}
document.addEventListener('DOMContentLoaded', function () {
  buildMoreMenu();
  var closeAll = initCategoryDropdowns();
  initPriorityNav(closeAll);
  initMobileDrawer();
  wrapTables();
  initToolForm();
  renderMath();
});
