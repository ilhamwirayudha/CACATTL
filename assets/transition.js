(function() {
    function setupTransition() {
        try {
            var doc = window.parent.document;
            var win = window.parent;
            if (!doc || !win) return;

            win.triggerMulaiAnalisisTransition = function(e) {
                var target = doc.getElementById('langkah-analisis') ||
                             doc.getElementById('step1-header-title') ||
                             doc.getElementById('step1-card-marker') ||
                             doc.querySelector('.glass-card') ||
                             doc.querySelector('[data-testid="stFileUploader"]');
                if (!target) return;

                if (e) {
                    if (e.preventDefault) e.preventDefault();
                    if (e.stopPropagation) e.stopPropagation();
                    if (e.stopImmediatePropagation) e.stopImmediatePropagation();
                }

                try {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                } catch(err) {}

                var candidates = [
                    doc.querySelector('[data-testid="stMain"]'),
                    doc.querySelector('[data-testid="stAppViewContainer"]'),
                    doc.querySelector('.main'),
                    doc.documentElement,
                    doc.body
                ];

                var rect = target.getBoundingClientRect();
                for (var i = 0; i < candidates.length; i++) {
                    var el = candidates[i];
                    if (el && el.scrollHeight > el.clientHeight) {
                        var currentY = el.scrollTop || 0;
                        var targetY = currentY + rect.top - 28;
                        try {
                            el.scrollTo({ top: targetY, behavior: 'smooth' });
                        } catch(err) {
                            el.scrollTop = targetY;
                        }
                    }
                }
            };

            win.triggerScrollToStep3 = function() {
                var target = doc.getElementById('step3-card-marker') || doc.getElementById('langkah-3-anchor');
                if (!target) return;

                var candidates = [
                    doc.querySelector('[data-testid="stAppViewContainer"]'),
                    doc.querySelector('.main'),
                    doc.querySelector('section[data-testid="stMain"]'),
                    doc.documentElement,
                    doc.body
                ];

                var rect = target.getBoundingClientRect();
                var scrolled = false;

                for (var i = 0; i < candidates.length; i++) {
                    var el = candidates[i];
                    if (el && el.scrollHeight > el.clientHeight) {
                        var currentY = el.scrollTop || 0;
                        var targetY = currentY + rect.top - 24;
                        try {
                            el.scrollTo({ top: targetY, behavior: 'smooth' });
                            scrolled = true;
                        } catch(err) {
                            el.scrollTop = targetY;
                            scrolled = true;
                        }
                    }
                }

                try {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                } catch(err) {}

                if (!scrolled) {
                    try {
                        var winY = (win.pageYOffset || 0) + rect.top - 24;
                        win.scrollTo({ top: winY, behavior: 'smooth' });
                    } catch(err) {}
                }
            };

            // Global capture listener on parent document: intercepts click instantly with 0ms delay
            if (!win.__cacaTransitionHandlerInstalled) {
                win.__cacaTransitionHandlerInstalled = true;
                doc.addEventListener('click', function(e) {
                    var btn = e.target && e.target.closest ? e.target.closest('#btn-mulai-analisis') : null;
                    if (btn) {
                        win.triggerMulaiAnalisisTransition(e);
                    }

                    var runBtn = e.target && e.target.closest ? e.target.closest('button') : null;
                    if (runBtn && runBtn.innerText && runBtn.innerText.indexOf('Jalankan Komputasi Analisis') !== -1) {
                        setTimeout(function() {
                            if (win.triggerScrollToStep3) win.triggerScrollToStep3();
                        }, 50);
                    }
                }, true);
            }

            // Modal Protection: Modal hanya bisa ditutup dengan tombol 'X' di pojok kanan atas
            if (!win.__cacaModalProtectionInstalled) {
                win.__cacaModalProtectionInstalled = true;

                function getActiveModal() {
                    return doc.querySelector('div[role="dialog"]') ||
                           doc.querySelector('div[data-testid="stDialog"] div[role="dialog"]');
                }

                // 1. Blok tombol ESC pada keyboard
                doc.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape' || e.keyCode === 27) {
                        var modal = getActiveModal();
                        if (modal) {
                            e.stopImmediatePropagation();
                            e.stopPropagation();
                            e.preventDefault();
                        }
                    }
                }, true);

                // 2. Blok klik di luar modal (backdrop / cursor di area luar dialog)
                function blockOutsideClick(e) {
                    var modal = getActiveModal();
                    if (modal) {
                        // Jangan blok klik pada dropdown popover / portal menu / selectbox BaseWeb
                        if (e.target && e.target.closest && (
                            e.target.closest('[data-baseweb="popover"]') ||
                            e.target.closest('[data-baseweb="menu"]') ||
                            e.target.closest('[role="listbox"]') ||
                            e.target.closest('[role="option"]') ||
                            e.target.closest('[data-baseweb="select"]') ||
                            e.target.closest('[data-testid="stSelectboxVirtualDropdown"]') ||
                            e.target.closest('[data-baseweb="portal"]') ||
                            e.target.closest('[data-testid="stPortal"]')
                        )) {
                            return;
                        }
                        // Jika target klik BUKAN di dalam modal dialog, cegah penutupan modal
                        if (!modal.contains(e.target)) {
                            e.stopImmediatePropagation();
                            e.stopPropagation();
                            e.preventDefault();
                        }
                    }
                }

                doc.addEventListener('mousedown', blockOutsideClick, true);
                doc.addEventListener('click', blockOutsideClick, true);
                doc.addEventListener('pointerdown', blockOutsideClick, true);
            }

            // Scroll Position Helpers & Persistence
            win.getCurrentScrollY = function() {
                var maxScroll = 0;
                var candidates = [
                    doc.querySelector('[data-testid="stMain"]'),
                    doc.querySelector('section.main'),
                    doc.querySelector('.main'),
                    doc.querySelector('[data-testid="stAppViewContainer"]'),
                    doc.documentElement,
                    doc.body
                ];
                for (var i = 0; i < candidates.length; i++) {
                    var el = candidates[i];
                    if (el && el.scrollTop && el.scrollTop > maxScroll) {
                        maxScroll = el.scrollTop;
                    }
                }
                var winY = win.pageYOffset || win.scrollY || (doc.documentElement ? doc.documentElement.scrollTop : 0) || (doc.body ? doc.body.scrollTop : 0);
                if (winY > maxScroll) maxScroll = winY;
                return maxScroll;
            };

            win.scrollToY = function(targetY, behavior) {
                var mode = behavior || 'instant';
                var candidates = [
                    doc.querySelector('[data-testid="stMain"]'),
                    doc.querySelector('section.main'),
                    doc.querySelector('.main'),
                    doc.querySelector('[data-testid="stAppViewContainer"]'),
                    doc.documentElement,
                    doc.body
                ];
                for (var i = 0; i < candidates.length; i++) {
                    var el = candidates[i];
                    if (el && el.scrollHeight > el.clientHeight) {
                        try {
                            el.scrollTo({ top: targetY, behavior: mode });
                        } catch(e) {
                            try { el.scrollTop = targetY; } catch(err) {}
                        }
                    }
                }
                try {
                    win.scrollTo({ top: targetY, behavior: mode });
                } catch(e) {
                    try { win.scrollTo(0, targetY); } catch(err) {}
                }
            };

            win.restoreCacaScroll = function(behavior) {
                var saved = 0;
                try {
                    saved = parseInt(sessionStorage.getItem('caca_scroll_pos') || '0', 10);
                } catch(e) {}

                if (saved > 120) {
                    win.scrollToY(saved, behavior || 'instant');
                } else {
                    var marker = doc.getElementById('step3-card-marker') || doc.getElementById('langkah-3-anchor');
                    if (marker) {
                        try {
                            marker.scrollIntoView({ behavior: behavior || 'instant', block: 'start' });
                        } catch(e) {}
                    }
                }
            };

            // Simpan posisi scroll secara kontinu dan saat beforeunload
            if (!win.__cacaScrollPersistenceInstalled) {
                win.__cacaScrollPersistenceInstalled = true;

                var saveScrollTimer = null;
                function saveScrollPos() {
                    clearTimeout(saveScrollTimer);
                    saveScrollTimer = setTimeout(function() {
                        var y = win.getCurrentScrollY ? win.getCurrentScrollY() : 0;
                        if (y > 60) {
                            try { sessionStorage.setItem('caca_scroll_pos', y); } catch(e) {}
                        }
                    }, 50);
                }

                win.addEventListener('scroll', saveScrollPos, { passive: true });
                doc.addEventListener('scroll', saveScrollPos, { passive: true, capture: true });
                doc.addEventListener('pointerdown', function() {
                    var y = win.getCurrentScrollY ? win.getCurrentScrollY() : 0;
                    if (y > 60) {
                        try { sessionStorage.setItem('caca_scroll_pos', y); } catch(e) {}
                    }
                }, { passive: true, capture: true });
                win.addEventListener('beforeunload', function() {
                    var y = win.getCurrentScrollY ? win.getCurrentScrollY() : 0;
                    if (y > 60) {
                        try { sessionStorage.setItem('caca_scroll_pos', y); } catch(e) {}
                    }
                });

                var candidates = [
                    doc.querySelector('[data-testid="stMain"]'),
                    doc.querySelector('section.main'),
                    doc.querySelector('.main'),
                    doc.querySelector('[data-testid="stAppViewContainer"]')
                ];
                for (var i = 0; i < candidates.length; i++) {
                    if (candidates[i]) {
                        candidates[i].addEventListener('scroll', saveScrollPos, { passive: true });
                    }
                }

                // Pemulihan scroll otomatis saat awal dimuat (dengan retry interval bertahap)
                var initialSaved = 0;
                try { initialSaved = parseInt(sessionStorage.getItem('caca_scroll_pos') || '0', 10); } catch(e) {}
                if (initialSaved > 120) {
                    var retries = [150, 300, 600, 1000, 1500, 2200];
                    retries.forEach(function(delay) {
                        setTimeout(function() {
                            win.restoreCacaScroll('instant');
                        }, delay);
                    });
                }
            }

        } catch (err) {
            console.error('CACA transition setup error:', err);
        }
    }

    setupTransition();
    var count = 0;
    var interval = setInterval(function() {
        count++;
        setupTransition();
        if (count > 25) clearInterval(interval);
    }, 100);
})();
