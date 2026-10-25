/**
 * Universal Top Progress Loader Engine
 * Provides instant YouTube/GitHub-style top progress line for page transitions,
 * form submissions, link navigations, and AJAX/HTMX events.
 */

(function () {
    'use strict';

    const TopLoader = {
        container: null,
        bar: null,
        status: 0,
        timer: null,
        isStarted: false,

        createDOM() {
            if (this.container && document.body.contains(this.container)) return;
            
            let container = document.getElementById('top-loader');
            if (!container) {
                container = document.createElement('div');
                container.id = 'top-loader';
                container.className = 'top-loader-container';
                container.setAttribute('role', 'progressbar');
                container.setAttribute('aria-hidden', 'true');

                const bar = document.createElement('div');
                bar.className = 'top-loader-bar';
                bar.id = 'top-loader-bar';

                const peg = document.createElement('div');
                peg.className = 'top-loader-peg';

                bar.appendChild(peg);
                container.appendChild(bar);

                if (document.body) {
                    document.body.insertBefore(container, document.body.firstChild);
                }
            }

            this.container = container;
            this.bar = container.querySelector('.top-loader-bar');
        },

        start() {
            this.createDOM();
            if (this.isStarted) return;
            this.isStarted = true;
            this.set(0.18);
            this.trickle();
        },

        set(n) {
            this.createDOM();
            if (!this.bar || !this.container) return;

            this.status = Math.min(Math.max(n, 0), 1);
            this.container.classList.add('is-active');
            this.bar.style.width = (this.status * 100) + '%';
        },

        trickle() {
            clearInterval(this.timer);
            this.timer = setInterval(() => {
                if (this.status >= 0.92) {
                    clearInterval(this.timer);
                    return;
                }
                // Slow down as it approaches 92%
                const remaining = 0.94 - this.status;
                const inc = Math.max(0.015, remaining * 0.18);
                this.set(this.status + inc);
            }, 200);
        },

        inc(amount) {
            let n = this.status;
            if (!this.isStarted) {
                this.start();
                return;
            }
            if (typeof amount !== 'number') {
                amount = (1 - n) * 0.1;
            }
            this.set(n + amount);
        },

        done() {
            clearInterval(this.timer);
            if (!this.isStarted && (!this.container || !this.container.classList.contains('is-active'))) {
                return;
            }

            this.set(1.0);
            setTimeout(() => {
                if (this.container) {
                    this.container.classList.remove('is-active');
                    setTimeout(() => {
                        this.isStarted = false;
                        this.status = 0;
                        if (this.bar) this.bar.style.width = '0%';
                    }, 250);
                } else {
                    this.isStarted = false;
                    this.status = 0;
                }
            }, 180);
        },

        bindEvents() {
            // 1. Initial Page Load Lifecycle
            if (document.readyState === 'loading') {
                this.start();
                document.addEventListener('DOMContentLoaded', () => this.set(0.75));
                window.addEventListener('load', () => this.done());
            } else {
                this.start();
                setTimeout(() => this.done(), 120);
            }

            // 2. Navigation Link Clicks
            document.addEventListener('click', (e) => {
                const link = e.target.closest('a');
                if (!link) return;

                const href = link.getAttribute('href');
                if (!href) return;

                // Ignore anchors, javascript, modifier clicks, new tabs, downloads, quick prints
                if (
                    href.startsWith('#') ||
                    href.startsWith('javascript:') ||
                    link.target === '_blank' ||
                    link.hasAttribute('download') ||
                    link.hasAttribute('data-no-loader') ||
                    link.hasAttribute('data-export-excel') ||
                    link.hasAttribute('data-export-pdf') ||
                    href.includes('?print=1') ||
                    e.ctrlKey || e.metaKey || e.shiftKey || e.altKey
                ) {
                    return;
                }

                // Verify same origin
                try {
                    const targetUrl = new URL(link.href, window.location.href);
                    if (targetUrl.origin === window.location.origin) {
                        TopLoader.start();
                    }
                } catch (_) {}
            });

            // 3. Form Submissions
            document.addEventListener('submit', (e) => {
                const form = e.target;
                if (!form || form.target === '_blank' || form.hasAttribute('data-no-loader')) return;
                TopLoader.start();
            });

            // 4. HTMX Integration (if used on page)
            document.addEventListener('htmx:beforeRequest', () => TopLoader.start());
            document.addEventListener('htmx:afterOnLoad', () => TopLoader.done());
            document.addEventListener('htmx:responseError', () => TopLoader.done());
            document.addEventListener('htmx:sendError', () => TopLoader.done());

            // 5. Window unload / refresh
            window.addEventListener('beforeunload', () => TopLoader.start());

            // 6. Support Back/Forward Cache (bfcache)
            window.addEventListener('pageshow', (event) => {
                if (event.persisted) {
                    TopLoader.done();
                }
            });
        }
    };

    window.TopLoader = TopLoader;

    // Initialize immediately
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            TopLoader.createDOM();
            TopLoader.bindEvents();
        });
    } else {
        TopLoader.createDOM();
        TopLoader.bindEvents();
    }
})();
