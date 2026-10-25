/**
 * Universal Advanced Table System for Showroom Management ERP
 * Provides Zoho Books-style high-density, professional tables with:
 * 1. Dynamic Column Show/Hide toggling with persistent localStorage memory
 * 2. Multi-type interactive sorting (Ascending / Descending) for each and every column
 * 3. Instant client-side & server-side Export to Excel (CSV/XLSX)
 * 4. High-fidelity A4 Print & Export to PDF
 * 5. Real-time client-side search filtering and dynamic record counts
 */

(function () {
    'use strict';

    function initAdvancedTables(container) {
        const root = container || document;
        const wrappers = root.querySelectorAll('[data-advanced-table], .advanced-table-card');

        wrappers.forEach(function (wrapper, wrapIdx) {
            if (wrapper._advTableInitialized) return;
            wrapper._advTableInitialized = true;

            const table = wrapper.querySelector('table');
            if (!table) return;

            const thead = table.querySelector('thead');
            const tbody = table.querySelector('tbody');
            if (!thead || !tbody) return;

            const tableId = wrapper.getAttribute('data-table-id') || table.id || ('adv-table-' + wrapIdx);
            const tableTitle = wrapper.getAttribute('data-table-title') || document.title.split('|')[0].trim() || 'Data_Export';
            const headers = Array.from(thead.querySelectorAll('th'));

            // -------------------------------------------------------------
            // 1. Column Show/Hide Dropdown Integration
            // -------------------------------------------------------------
            const columnsDropdownMenu = wrapper.querySelector('[data-columns-dropdown-menu]');
            const savedHiddenCols = JSON.parse(localStorage.getItem('table_cols_' + tableId) || '[]');

            if (columnsDropdownMenu) {
                columnsDropdownMenu.innerHTML = '';
                
                // Add header info
                const headerInfo = document.createElement('div');
                headerInfo.className = 'px-3 py-2 text-[11px] font-bold text-slate-700 bg-slate-50 border-b border-slate-200 flex items-center justify-between';
                headerInfo.innerHTML = '<span>Show / Hide Columns</span><button type="button" class="text-blue-600 hover:underline text-[10px] reset-cols-btn">Reset All</button>';
                columnsDropdownMenu.appendChild(headerInfo);

                const listContainer = document.createElement('div');
                listContainer.className = 'p-2 max-h-64 overflow-y-auto space-y-1';
                columnsDropdownMenu.appendChild(listContainer);

                headers.forEach(function (th, colIdx) {
                    // Skip action column from hiding if marked
                    const colName = (th.getAttribute('data-col-name') || th.innerText || '').trim();
                    if (!colName || th.hasAttribute('data-no-toggle') || colName.toLowerCase() === 'actions' || colName.toLowerCase() === 'action') return;

                    const label = document.createElement('label');
                    label.className = 'flex items-center gap-2 px-2 py-1.5 rounded hover:bg-slate-100 text-xs text-slate-700 cursor-pointer select-none';

                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.checked = !savedHiddenCols.includes(colIdx);
                    checkbox.className = 'rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-3.5 h-3.5';

                    const textSpan = document.createElement('span');
                    textSpan.textContent = colName;
                    textSpan.className = 'truncate';

                    label.appendChild(checkbox);
                    label.appendChild(textSpan);
                    listContainer.appendChild(label);

                    checkbox.addEventListener('change', function () {
                        toggleColumn(colIdx, checkbox.checked);
                    });

                    // Initial state application
                    if (savedHiddenCols.includes(colIdx)) {
                        toggleColumn(colIdx, false, false);
                    }
                });

                const resetBtn = headerInfo.querySelector('.reset-cols-btn');
                if (resetBtn) {
                    resetBtn.addEventListener('click', function (e) {
                        e.stopPropagation();
                        localStorage.removeItem('table_cols_' + tableId);
                        listContainer.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
                            cb.checked = true;
                        });
                        headers.forEach(function (th, idx) {
                            toggleColumn(idx, true, false);
                        });
                    });
                }

                columnsDropdownMenu.addEventListener('click', function (e) {
                    e.stopPropagation();
                });

                const columnsDropdownToggle = wrapper.querySelector('[data-columns-toggle]');
                if (columnsDropdownToggle) {
                    columnsDropdownToggle.addEventListener('click', function (e) {
                        e.stopPropagation();
                        columnsDropdownMenu.classList.toggle('hidden');
                    });
                    document.addEventListener('click', function (e) {
                        if (!columnsDropdownMenu.contains(e.target) && !columnsDropdownToggle.contains(e.target)) {
                            columnsDropdownMenu.classList.add('hidden');
                        }
                    });
                }
            }

            function toggleColumn(colIdx, isVisible, saveToStorage = true) {
                const th = headers[colIdx];
                if (th) {
                    th.style.display = isVisible ? '' : 'none';
                }
                const rows = tbody.querySelectorAll('tr');
                rows.forEach(function (row) {
                    if (row.children[colIdx]) {
                        row.children[colIdx].style.display = isVisible ? '' : 'none';
                    }
                });

                if (saveToStorage) {
                    let hidden = JSON.parse(localStorage.getItem('table_cols_' + tableId) || '[]');
                    if (!isVisible && !hidden.includes(colIdx)) {
                        hidden.push(colIdx);
                    } else if (isVisible && hidden.includes(colIdx)) {
                        hidden = hidden.filter(i => i !== colIdx);
                    }
                    localStorage.setItem('table_cols_' + tableId, JSON.stringify(hidden));
                }
            }

            // -------------------------------------------------------------
            // 2. Interactive Column Sorting (Ascending / Descending)
            // -------------------------------------------------------------
            headers.forEach(function (th, colIdx) {
                if (th.hasAttribute('data-no-sort')) return;
                const text = th.innerText.trim();
                if (!text || text.toLowerCase() === 'actions') return;

                th.style.cursor = 'pointer';
                th.setAttribute('title', 'Click to sort ' + text);
                th.classList.add('select-none', 'group');

                // Ensure sort icon exists
                let sortIcon = th.querySelector('.sort-icon');
                if (!sortIcon) {
                    sortIcon = document.createElement('i');
                    sortIcon.className = 'fas fa-sort sort-icon ml-1.5 text-slate-400 group-hover:text-white transition-colors text-[10px]';
                    th.appendChild(sortIcon);
                }

                th.addEventListener('click', function () {
                    const currentDir = th.getAttribute('data-sort-dir') || 'none';
                    const newDir = currentDir === 'asc' ? 'desc' : 'asc';

                    // Reset all other headers
                    headers.forEach(function (h) {
                        h.removeAttribute('data-sort-dir');
                        const icon = h.querySelector('.sort-icon');
                        if (icon) {
                            icon.className = 'fas fa-sort sort-icon ml-1.5 text-slate-400 group-hover:text-white transition-colors text-[10px]';
                        }
                    });

                    th.setAttribute('data-sort-dir', newDir);
                    if (newDir === 'asc') {
                        sortIcon.className = 'fas fa-sort-up sort-icon ml-1.5 text-blue-400 text-[11px]';
                    } else {
                        sortIcon.className = 'fas fa-sort-down sort-icon ml-1.5 text-blue-400 text-[11px]';
                    }

                    sortTableByColumn(tbody, colIdx, newDir);
                    updateRowSerialNumbers(tbody);
                });
            });

            // -------------------------------------------------------------
            // 3. Export to Excel Button
            // -------------------------------------------------------------
            const exportExcelBtn = wrapper.querySelector('[data-export-excel]');
            if (exportExcelBtn) {
                exportExcelBtn.addEventListener('click', function (e) {
                    const serverUrl = exportExcelBtn.getAttribute('data-server-url');
                    // If a specialized backend Excel URL is given and user didn't request client export, use server
                    if (serverUrl && !exportExcelBtn.hasAttribute('data-client-export')) {
                        return; // Let standard link navigation proceed
                    }
                    e.preventDefault();
                    exportTableToExcel(table, tableTitle);
                });
            }

            // -------------------------------------------------------------
            // 4. Export to PDF Button
            // -------------------------------------------------------------
            const exportPdfBtn = wrapper.querySelector('[data-export-pdf]');
            if (exportPdfBtn) {
                exportPdfBtn.addEventListener('click', function (e) {
                    const serverUrl = exportPdfBtn.getAttribute('data-server-url');
                    if (serverUrl && !exportPdfBtn.hasAttribute('data-client-export')) {
                        return;
                    }
                    e.preventDefault();
                    exportTableToPdf(table, tableTitle, wrapper);
                });
            }

            // -------------------------------------------------------------
            // 5. In-Page Fast Search Filtering & Dynamic Count
            // -------------------------------------------------------------
            const searchInput = wrapper.querySelector('[data-table-search]') || document.querySelector(`[data-table-search="${tableId}"]`);
            const countDisplay = wrapper.querySelector('[data-table-count]');

            if (searchInput) {
                searchInput.addEventListener('input', function (e) {
                    const query = e.target.value.toLowerCase().trim();
                    const rows = tbody.querySelectorAll('tr:not(.empty-row)');
                    let matchCount = 0;

                    rows.forEach(function (row) {
                        const rowText = row.innerText.toLowerCase();
                        if (!query || rowText.includes(query)) {
                            row.style.display = '';
                            matchCount++;
                        } else {
                            row.style.display = 'none';
                        }
                    });

                    if (countDisplay) {
                        countDisplay.textContent = `Showing ${matchCount} of ${rows.length} entries`;
                    }
                });
            }
        });
    }

    /**
     * Sorts table rows numerically, chronologically, or alphabetically
     */
    function sortTableByColumn(tbody, colIdx, direction) {
        const rows = Array.from(tbody.querySelectorAll('tr:not(.empty-row)'));
        if (rows.length === 0) return;

        rows.sort(function (rowA, rowB) {
            const cellA = rowA.children[colIdx];
            const cellB = rowB.children[colIdx];
            if (!cellA || !cellB) return 0;

            const textA = (cellA.getAttribute('data-sort-val') || cellA.innerText || '').trim();
            const textB = (cellB.getAttribute('data-sort-val') || cellB.innerText || '').trim();

            // Try clean numeric parse (supports currency like ₹50,000.00, percentages, etc.)
            const numA = parseFloat(textA.replace(/[₹$,%]/g, '').replace(/,/g, ''));
            const numB = parseFloat(textB.replace(/[₹$,%]/g, '').replace(/,/g, ''));

            if (!isNaN(numA) && !isNaN(numB) && !textA.includes('/') && !textA.includes('-') && !textA.includes(':')) {
                return direction === 'asc' ? numA - numB : numB - numA;
            }

            // Try date parse
            const dateA = Date.parse(textA);
            const dateB = Date.parse(textB);
            if (!isNaN(dateA) && !isNaN(dateB)) {
                return direction === 'asc' ? dateA - dateB : dateB - dateA;
            }

            // Standard natural alphanumeric comparison
            return direction === 'asc'
                ? textA.localeCompare(textB, undefined, { numeric: true, sensitivity: 'base' })
                : textB.localeCompare(textA, undefined, { numeric: true, sensitivity: 'base' });
        });

        // Re-append sorted rows
        rows.forEach(function (row) {
            tbody.appendChild(row);
        });
    }

    /**
     * Re-calculates sequential row serial badges if present (.row-sr)
     */
    function updateRowSerialNumbers(tbody) {
        const srElements = tbody.querySelectorAll('.row-sr');
        let counter = 1;
        srElements.forEach(function (el) {
            const row = el.closest('tr');
            if (row && row.style.display !== 'none') {
                el.textContent = counter;
                counter++;
            }
        });
    }

    /**
     * Exports visible table columns & data into a clean, Excel-compatible CSV with UTF-8 BOM
     */
    function exportTableToExcel(table, filename) {
        const thead = table.querySelector('thead');
        const tbody = table.querySelector('tbody');
        if (!thead || !tbody) return;

        const visibleCols = [];
        const headers = Array.from(thead.querySelectorAll('th'));

        headers.forEach(function (th, idx) {
            const isHidden = window.getComputedStyle(th).display === 'none';
            const name = (th.getAttribute('data-col-name') || th.innerText || '').trim();
            if (!isHidden && name.toLowerCase() !== 'actions') {
                visibleCols.push({ index: idx, name: name });
            }
        });

        let csvContent = '\uFEFF'; // UTF-8 BOM for Excel to display Indian characters and currency properly
        // Header row
        csvContent += visibleCols.map(c => `"${c.name.replace(/"/g, '""')}"`).join(',') + '\r\n';

        // Data rows
        const rows = tbody.querySelectorAll('tr:not(.empty-row)');
        rows.forEach(function (row) {
            if (window.getComputedStyle(row).display === 'none') return;
            const rowVals = [];
            visibleCols.forEach(function (c) {
                const cell = row.children[c.index];
                let text = cell ? (cell.getAttribute('data-export-val') || cell.innerText || '').trim() : '';
                // Clean newlines
                text = text.replace(/[\r\n]+/g, ' ');
                rowVals.push(`"${text.replace(/"/g, '""')}"`);
            });
            csvContent += rowVals.join(',') + '\r\n';
        });

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const cleanName = (filename || 'Report').replace(/[^a-zA-Z0-9_-]/g, '_');
        const dateStr = new Date().toISOString().slice(0, 10);
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.setAttribute('download', `${cleanName}_${dateStr}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    /**
     * High-fidelity A4 Print & PDF Preview of the data table
     */
    function exportTableToPdf(table, reportTitle, wrapper) {
        const thead = table.querySelector('thead');
        const tbody = table.querySelector('tbody');
        if (!thead || !tbody) return;

        const visibleCols = [];
        const headers = Array.from(thead.querySelectorAll('th'));

        headers.forEach(function (th, idx) {
            const isHidden = window.getComputedStyle(th).display === 'none';
            const name = (th.getAttribute('data-col-name') || th.innerText || '').trim();
            if (!isHidden && name.toLowerCase() !== 'actions') {
                visibleCols.push({ index: idx, name: name });
            }
        });

        const printWindow = window.open('', '_blank');
        if (!printWindow) {
            alert('Please allow popups to export the table to PDF.');
            return;
        }

        const dateStr = new Date().toLocaleDateString('en-IN', {
            day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
        });

        let tableHtml = '<table class="pdf-table"><thead><tr>';
        visibleCols.forEach(function (c) {
            tableHtml += `<th>${c.name}</th>`;
        });
        tableHtml += '</tr></thead><tbody>';

        const rows = tbody.querySelectorAll('tr:not(.empty-row)');
        rows.forEach(function (row) {
            if (window.getComputedStyle(row).display === 'none') return;
            tableHtml += '<tr>';
            visibleCols.forEach(function (c) {
                const cell = row.children[c.index];
                let text = cell ? cell.innerText.trim() : '';
                tableHtml += `<td>${text}</td>`;
            });
            tableHtml += '</tr>';
        });
        tableHtml += '</tbody></table>';

        const html = `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>${reportTitle}</title>
    <style>
        @page { size: A4 landscape; margin: 12mm; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #1e293b; margin: 0; padding: 15px; font-size: 11px; }
        .header { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #0f172a; padding-bottom: 8px; margin-bottom: 12px; }
        .title { font-size: 16px; font-weight: 800; color: #0f172a; text-transform: uppercase; letter-spacing: 0.5px; }
        .meta { font-size: 10px; color: #64748b; font-weight: 500; }
        .pdf-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
        .pdf-table th { background-color: #0f172a; color: #ffffff; text-align: left; padding: 6px 8px; font-size: 10px; text-transform: uppercase; font-weight: 700; border: 1px solid #0f172a; }
        .pdf-table td { padding: 6px 8px; border: 1px solid #e2e8f0; font-size: 10px; color: #1e293b; }
        .pdf-table tr:nth-child(even) td { background-color: #f8fafc; }
        .footer { margin-top: 15px; display: flex; justify-content: space-between; font-size: 9px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 6px; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="title">${reportTitle}</div>
            <div class="meta">Showroom Management ERP &bull; Official Register Record</div>
        </div>
        <div class="meta">Generated: ${dateStr}</div>
    </div>
    ${tableHtml}
    <div class="footer">
        <div>Showroom Management ERP</div>
        <div>Confidential &bull; Page 1 of 1</div>
    </div>
    <script>
        window.onload = function() {
            setTimeout(function() {
                window.print();
            }, 300);
        };
    </script>
</body>
</html>`;

        printWindow.document.open();
        printWindow.document.write(html);
        printWindow.document.close();
    }

    // Expose globally
    window.initAdvancedTables = initAdvancedTables;

    // Run on Ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initAdvancedTables();
        });
    } else {
        initAdvancedTables();
    }

    document.addEventListener('htmx:afterSwap', function (e) {
        initAdvancedTables(e.detail.target || document);
    });

    document.addEventListener('alpine:initialized', function () {
        initAdvancedTables();
    });

    window.addEventListener('load', function () {
        initAdvancedTables();
    });
})();
