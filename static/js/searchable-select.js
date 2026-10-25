/**
 * Universal Searchable Dropdown Engine
 * Zero external dependencies. Converts any standard HTML <select> into a searchable floating dropdown
 * matching the modern ERP layout from the design specifications.
 */
(function () {
  'use strict';

  let activeInstance = null;

  class SearchableSelectInstance {
    constructor(selectElement) {
      this.select = selectElement;
      this.menuEl = null;
      this.searchEl = null;
      this.optionsContainer = null;
      this.focusedOptionIndex = -1;
      this.visibleOptions = [];
      this.allOptions = [];
      this.query = '';
      this.isOpen = false;

      this.init();
    }

    init() {
      if (this.select.dataset.searchableUpgraded === 'true') return;
      this.select.dataset.searchableUpgraded = 'true';
      this.select._searchableInstance = this;

      // 1. Build Trigger Button
      this.triggerEl = document.createElement('div');
      
      // Preserve any custom sizing classes or width classes if present
      let extraClasses = '';
      if (this.select.className) {
        // Filter out classes that might disrupt trigger styling
        const filtered = this.select.className
          .split(' ')
          .filter(c => !c.includes('border') && !c.includes('bg-') && !c.includes('px-') && !c.includes('py-') && !c.includes('text-'))
          .join(' ');
        if (filtered) extraClasses = ' ' + filtered;
      }
      this.triggerEl.className = 'searchable-select-trigger' + extraClasses;
      this.triggerEl.tabIndex = this.select.disabled ? -1 : 0;
      this.triggerEl.setAttribute('role', 'combobox');
      this.triggerEl.setAttribute('aria-expanded', 'false');
      this.triggerEl.setAttribute('aria-haspopup', 'listbox');

      this.labelEl = document.createElement('span');
      this.labelEl.className = 'searchable-select-label';

      this.chevronEl = document.createElement('span');
      this.chevronEl.className = 'searchable-select-chevron';
      this.chevronEl.innerHTML = `
        <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      `;

      this.triggerEl.appendChild(this.labelEl);
      this.triggerEl.appendChild(this.chevronEl);

      // 2. Hide Native Select
      this.select.classList.add('searchable-select-hidden');
      this.select.tabIndex = -1;

      // 3. Insert Trigger right after select
      if (this.select.parentNode) {
        this.select.parentNode.insertBefore(this.triggerEl, this.select.nextSibling);
      }

      // 4. Initial Sync
      this.readOptions();
      this.updateLabel();

      // 5. Events
      this.bindEvents();
    }

    readOptions() {
      this.allOptions = [];
      const optionElements = Array.from(this.select.querySelectorAll('option'));
      optionElements.forEach((opt, idx) => {
        this.allOptions.push({
          index: idx,
          value: opt.value,
          text: opt.textContent.trim(),
          selected: opt.selected || (this.select.value === opt.value),
          disabled: opt.disabled,
          element: opt
        });
      });
      this.visibleOptions = [...this.allOptions];
    }

    updateLabel() {
      const currentVal = this.select.value;
      const selected = this.allOptions.find((o) => o.value === currentVal) || this.allOptions.find((o) => o.selected) || this.allOptions[0];
      
      let iconHtml = '';
      if (this.select.dataset.icon) {
        iconHtml = `<i class="${this.select.dataset.icon} text-slate-400 mr-2 text-[11px] shrink-0 pointer-events-none"></i>`;
      }

      if (selected && selected.value !== '') {
        this.labelEl.innerHTML = iconHtml + `<span class="truncate">${this.escapeHtml(selected.text)}</span>`;
        this.labelEl.classList.remove('is-placeholder');
      } else {
        const placeholder = this.select.getAttribute('data-placeholder') || this.select.getAttribute('placeholder') || (selected ? selected.text : 'Select an option');
        this.labelEl.innerHTML = iconHtml + `<span class="truncate">${this.escapeHtml(placeholder)}</span>`;
        this.labelEl.classList.add('is-placeholder');
      }
    }

    sync() {
      this.readOptions();
      this.updateLabel();
      if (this.isOpen) {
        this.filter(this.query);
      }
    }

    bindEvents() {
      this.triggerEl.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.toggle();
      });

      this.triggerEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
          e.preventDefault();
          this.open();
        }
      });

      // Sync back if programmatically changed via native select
      this.select.addEventListener('change', () => {
        this.readOptions();
        this.updateLabel();
      });
    }

    toggle() {
      if (this.isOpen) this.close();
      else this.open();
    }

    open() {
      if (this.select.disabled || this.isOpen) return;
      if (activeInstance && activeInstance !== this) {
        activeInstance.close();
      }

      this.readOptions();
      this.buildMenu();
      this.positionMenu();

      this.isOpen = true;
      activeInstance = this;
      this.triggerEl.classList.add('is-active');
      this.triggerEl.setAttribute('aria-expanded', 'true');

      setTimeout(() => {
        if (this.searchEl) this.searchEl.focus();
      }, 30);

      this.bindGlobalListeners();
    }

    close() {
      if (!this.isOpen) return;
      if (this.menuEl && this.menuEl.parentNode) {
        this.menuEl.parentNode.removeChild(this.menuEl);
      }
      this.menuEl = null;
      this.isOpen = false;
      this.query = '';
      this.triggerEl.classList.remove('is-active');
      this.triggerEl.setAttribute('aria-expanded', 'false');

      if (activeInstance === this) activeInstance = null;
      this.unbindGlobalListeners();
    }

    buildMenu() {
      this.menuEl = document.createElement('div');
      this.menuEl.className = 'searchable-select-menu';

      // Search Header
      const header = document.createElement('div');
      header.className = 'searchable-select-search-header';

      header.innerHTML = `
        <span class="searchable-select-search-icon">
          <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </span>
      `;

      this.searchEl = document.createElement('input');
      this.searchEl.type = 'text';
      this.searchEl.className = 'searchable-select-search-input';
      this.searchEl.placeholder = 'Type to search...';
      this.searchEl.autocomplete = 'off';

      const clearBtn = document.createElement('button');
      clearBtn.type = 'button';
      clearBtn.className = 'searchable-select-search-clear';
      clearBtn.innerHTML = `
        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      `;
      clearBtn.style.display = 'none';

      clearBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        e.preventDefault();
        this.searchEl.value = '';
        this.filter('');
        this.searchEl.focus();
        clearBtn.style.display = 'none';
      });

      this.searchEl.addEventListener('input', (e) => {
        const val = e.target.value;
        clearBtn.style.display = val.length > 0 ? 'flex' : 'none';
        this.filter(val);
      });

      this.searchEl.addEventListener('keydown', (e) => this.handleKeydown(e));

      header.appendChild(this.searchEl);
      header.appendChild(clearBtn);
      this.menuEl.appendChild(header);

      // Options list container
      this.optionsContainer = document.createElement('div');
      this.optionsContainer.className = 'searchable-select-options-list';
      this.menuEl.appendChild(this.optionsContainer);

      document.body.appendChild(this.menuEl);
      this.renderOptions();
    }

    positionMenu() {
      if (!this.menuEl || !this.triggerEl) return;
      const rect = this.triggerEl.getBoundingClientRect();
      const menuWidth = Math.max(rect.width, 220);
      const viewportHeight = window.innerHeight;
      const spaceBelow = viewportHeight - rect.bottom;
      const spaceAbove = rect.top;
      const estimatedHeight = Math.min(260, (this.visibleOptions.length * 32) + 52);

      let top = rect.bottom + 4;
      let flipped = false;

      if (spaceBelow < estimatedHeight && spaceAbove > spaceBelow) {
        top = rect.top - estimatedHeight - 4;
        flipped = true;
      }

      let left = rect.left;
      if (left + menuWidth > window.innerWidth - 10) {
        left = window.innerWidth - menuWidth - 10;
      }
      if (left < 10) left = 10;

      this.menuEl.style.width = `${menuWidth}px`;
      this.menuEl.style.top = `${Math.max(4, top)}px`;
      this.menuEl.style.left = `${left}px`;
      this.menuEl.classList.toggle('is-flipped', flipped);
    }

    filter(query) {
      this.query = query.trim().toLowerCase();
      if (!this.query) {
        this.visibleOptions = [...this.allOptions];
      } else {
        this.visibleOptions = this.allOptions.filter((opt) =>
          opt.text.toLowerCase().includes(this.query)
        );
      }
      this.focusedOptionIndex = -1;
      this.renderOptions();
      this.positionMenu();
    }

    renderOptions() {
      this.optionsContainer.innerHTML = '';

      if (this.visibleOptions.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'searchable-select-empty';
        empty.textContent = 'No matching options';
        this.optionsContainer.appendChild(empty);
        return;
      }

      const currentVal = this.select.value;

      this.visibleOptions.forEach((opt, idx) => {
        const row = document.createElement('div');
        row.className = 'searchable-select-option';
        const isSelected = (opt.value === currentVal) || (opt.selected && !currentVal);
        if (isSelected) row.classList.add('is-selected');
        if (idx === this.focusedOptionIndex) row.classList.add('is-focused');

        const label = document.createElement('span');
        label.className = 'searchable-select-option-text';

        if (this.query) {
          const regex = new RegExp(`(${this.escapeRegex(this.query)})`, 'gi');
          label.innerHTML = this.escapeHtml(opt.text).replace(regex, '<mark>$1</mark>');
        } else {
          label.textContent = opt.text;
        }

        row.appendChild(label);

        if (isSelected) {
          const check = document.createElement('span');
          check.className = 'searchable-select-check-icon';
          check.innerHTML = `
            <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          `;
          row.appendChild(check);
        }

        row.addEventListener('click', (e) => {
          e.stopPropagation();
          e.preventDefault();
          this.selectOption(opt);
        });

        this.optionsContainer.appendChild(row);
      });
    }

    selectOption(opt) {
      this.select.value = opt.value;
      this.select.dispatchEvent(new Event('change', { bubbles: true }));
      this.select.dispatchEvent(new Event('input', { bubbles: true }));
      this.readOptions();
      this.updateLabel();
      this.close();
      this.triggerEl.focus();
    }

    handleKeydown(e) {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        this.close();
        this.triggerEl.focus();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        e.stopPropagation();
        this.focusedOptionIndex = Math.min(this.focusedOptionIndex + 1, this.visibleOptions.length - 1);
        this.renderOptions();
        this.scrollFocusedIntoView();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        e.stopPropagation();
        this.focusedOptionIndex = Math.max(this.focusedOptionIndex - 1, 0);
        this.renderOptions();
        this.scrollFocusedIntoView();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        e.stopPropagation();
        if (this.focusedOptionIndex >= 0 && this.visibleOptions[this.focusedOptionIndex]) {
          this.selectOption(this.visibleOptions[this.focusedOptionIndex]);
        } else if (this.visibleOptions.length > 0) {
          // If no option highlighted, choose the first filtered option
          this.selectOption(this.visibleOptions[0]);
        }
      }
    }

    scrollFocusedIntoView() {
      const items = this.optionsContainer.querySelectorAll('.searchable-select-option');
      if (items[this.focusedOptionIndex]) {
        items[this.focusedOptionIndex].scrollIntoView({ block: 'nearest' });
      }
    }

    escapeRegex(str) {
      return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    bindGlobalListeners() {
      this._onDocumentClick = (e) => {
        if (!this.menuEl.contains(e.target) && !this.triggerEl.contains(e.target)) {
          this.close();
        }
      };
      this._onResizeOrScroll = () => this.positionMenu();

      document.addEventListener('mousedown', this._onDocumentClick);
      window.addEventListener('resize', this._onResizeOrScroll);
      window.addEventListener('scroll', this._onResizeOrScroll, true);
    }

    unbindGlobalListeners() {
      if (this._onDocumentClick) document.removeEventListener('mousedown', this._onDocumentClick);
      if (this._onResizeOrScroll) {
        window.removeEventListener('resize', this._onResizeOrScroll);
        window.removeEventListener('scroll', this._onResizeOrScroll, true);
      }
    }
  }

  const SearchableSelect = {
    upgrade: (select) => {
      if (!select || select.tagName !== 'SELECT') return null;
      if (select.hasAttribute('data-no-search') || select.classList.contains('no-search')) return null;
      if (select.id === 'pageSizeSelect' || select.id === 'tablePageSize') return null;
      if (select.multiple) return null;
      if (select.dataset.searchableUpgraded === 'true') return select._searchableInstance || null;
      return new SearchableSelectInstance(select);
    },
    initAll: (root = document) => {
      if (!root) return;
      root.querySelectorAll('select:not([data-no-search]):not(.no-search):not(#pageSizeSelect):not(#tablePageSize):not(.searchable-select-hidden)').forEach((el) => {
        SearchableSelect.upgrade(el);
      });
    }
  };

  window.SearchableSelect = SearchableSelect;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => SearchableSelect.initAll());
  } else {
    SearchableSelect.initAll();
  }
})();
