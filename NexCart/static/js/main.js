/**
 * NexCart - Main JavaScript File
 * Handles Mobile Menu, Sidebars, Alerts, Modals, Graphical Animations & Micro-Interactions
 */

document.addEventListener("DOMContentLoaded", function () {
    // ----------------------------------------------------
    // 1. Mobile Navbar Toggle
    // ----------------------------------------------------
    const menuButton = document.getElementById("mobileMenuButton");
    const navbarMenu = document.getElementById("navbarMenu");

    if (menuButton && navbarMenu) {
        menuButton.addEventListener("click", function (e) {
            e.stopPropagation();
            navbarMenu.classList.toggle("active");
            const expanded = navbarMenu.classList.contains("active");
            menuButton.setAttribute("aria-expanded", expanded);
        });

        // Close when clicking outside
        document.addEventListener("click", function (e) {
            if (!navbarMenu.contains(e.target) && !menuButton.contains(e.target)) {
                navbarMenu.classList.remove("active");
                menuButton.setAttribute("aria-expanded", "false");
            }
        });
    }

    // ----------------------------------------------------
    // 2. Seller Mobile Sidebar Toggle
    // ----------------------------------------------------
    const sellerToggle = document.getElementById("sellerMobileToggle");
    const sellerSidebar = document.getElementById("sellerSidebar");

    if (sellerToggle && sellerSidebar) {
        sellerToggle.addEventListener("click", function (e) {
            e.stopPropagation();
            sellerSidebar.classList.toggle("active");
        });

        document.addEventListener("click", function (e) {
            if (!sellerSidebar.contains(e.target) && !sellerToggle.contains(e.target)) {
                sellerSidebar.classList.remove("active");
            }
        });
    }

    // ----------------------------------------------------
    // 3. Admin Mobile Sidebar Toggle
    // ----------------------------------------------------
    const adminToggle = document.getElementById("adminMobileToggle");
    const adminSidebar = document.getElementById("adminSidebar");

    if (adminToggle && adminSidebar) {
        adminToggle.addEventListener("click", function (e) {
            e.stopPropagation();
            adminSidebar.classList.toggle("active");
        });

        document.addEventListener("click", function (e) {
            if (!adminSidebar.contains(e.target) && !adminToggle.contains(e.target)) {
                adminSidebar.classList.remove("active");
            }
        });
    }

    // ----------------------------------------------------
    // 4. Auto-dismiss alerts with progress bar
    // ----------------------------------------------------
    const alerts = document.querySelectorAll(".messages-container .alert");
    alerts.forEach(function (alert) {
        // Add animated progress bar if not present
        if (!alert.querySelector(".alert-progress")) {
            const progressBar = document.createElement("div");
            progressBar.className = "alert-progress";
            alert.appendChild(progressBar);
        }

        setTimeout(function () {
            alert.style.opacity = "0";
            alert.style.transform = "translateX(40px) scale(0.95)";
            alert.style.transition = "all 0.35s cubic-bezier(0.16, 1, 0.3, 1)";
            setTimeout(function () {
                alert.remove();
            }, 350);
        }, 5000);
    });

    // ----------------------------------------------------
    // 5. Graphical Scroll Reveal Animations (IntersectionObserver)
    // ----------------------------------------------------
    initScrollReveal();

    // ----------------------------------------------------
    // 6. Interactive Button Ripple Effect
    // ----------------------------------------------------
    initButtonRipples();

    // ----------------------------------------------------
    // 7. Floating Scroll-To-Top Button
    // ----------------------------------------------------
    initScrollToTop();
});

// ----------------------------------------------------
// Scroll Reveal Engine
// ----------------------------------------------------
function initScrollReveal() {
    if (!('IntersectionObserver' in window)) {
        // Fallback for older browsers
        document.querySelectorAll('.reveal-on-scroll, .category-card, .product-card, .stat-card, .seller-menu-card').forEach(function (el) {
            el.classList.add('is-revealed');
        });
        return;
    }

    // Auto-tag grids with stagger delays
    const gridSelectors = ['.category-grid', '.product-grid', '.seller-stats', '.seller-menu', '.dashboard-cards'];
    gridSelectors.forEach(function (sel) {
        const grids = document.querySelectorAll(sel);
        grids.forEach(function (grid) {
            Array.from(grid.children).forEach(function (child, idx) {
                child.classList.add('reveal-on-scroll');
                const delayClass = 'stagger-' + ((idx % 8) + 1);
                child.classList.add(delayClass);
            });
        });
    });

    const revealElements = document.querySelectorAll('.reveal-on-scroll, .reveal-fade-in, .reveal-zoom-in');

    const observer = new IntersectionObserver(function (entries, obs) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-revealed');
                obs.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.12,
        rootMargin: '0px 0px -40px 0px'
    });

    revealElements.forEach(function (el) {
        observer.observe(el);
    });
}

// ----------------------------------------------------
// Interactive Button Ripples
// ----------------------------------------------------
function initButtonRipples() {
    const clickableSelectors = '.btn, .btn-primary, .btn-modal-confirm, .btn-modal-cancel, .product-btn, .category-card, .seller-menu-card, .view-product';
    const clickables = document.querySelectorAll(clickableSelectors);

    clickables.forEach(function (btn) {
        btn.classList.add('ripple-target');
        btn.addEventListener('click', function (e) {
            const rect = btn.getBoundingClientRect();
            const circle = document.createElement('span');
            const diameter = Math.max(rect.width, rect.height);
            const radius = diameter / 2;

            circle.style.width = circle.style.height = `${diameter}px`;
            circle.style.left = `${e.clientX - rect.left - radius}px`;
            circle.style.top = `${e.clientY - rect.top - radius}px`;
            circle.classList.add('ripple-wave');

            const existingWave = btn.querySelector('.ripple-wave');
            if (existingWave) {
                existingWave.remove();
            }

            btn.appendChild(circle);

            setTimeout(function () {
                circle.remove();
            }, 600);
        });
    });
}

// ----------------------------------------------------
// Floating Scroll-To-Top Button
// ----------------------------------------------------
function initScrollToTop() {
    let scrollBtn = document.getElementById('scrollToTopBtn');

    if (!scrollBtn) {
        scrollBtn = document.createElement('button');
        scrollBtn.id = 'scrollToTopBtn';
        scrollBtn.className = 'scroll-to-top';
        scrollBtn.setAttribute('aria-label', 'Scroll to top');
        scrollBtn.innerHTML = '<i class="fa-solid fa-arrow-up"></i>';
        document.body.appendChild(scrollBtn);
    }

    window.addEventListener('scroll', function () {
        if (window.scrollY > 280) {
            scrollBtn.classList.add('visible');
        } else {
            scrollBtn.classList.remove('visible');
        }
    }, { passive: true });

    scrollBtn.addEventListener('click', function () {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// ----------------------------------------------------
// 8. Logout Modal Helper Functions (Global)
// ----------------------------------------------------
function openLogoutModal(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    const modal = document.getElementById("logoutModal");
    if (modal) {
        modal.classList.add("active");
        document.body.style.overflow = "hidden";
    }
    return false;
}

function closeLogoutModal() {
    const modal = document.getElementById("logoutModal");
    if (modal) {
        modal.classList.remove("active");
        document.body.style.overflow = "";
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const modal = document.getElementById("logoutModal");
    if (modal) {
        modal.addEventListener("click", function (e) {
            if (e.target === modal) {
                closeLogoutModal();
            }
        });
    }

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            closeLogoutModal();
            const filterModal = document.getElementById("filterModal");
            if (filterModal) {
                filterModal.classList.remove("open");
            }
        }
    });
});

