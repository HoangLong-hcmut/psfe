let navbar = document.querySelector('.navbar');
let sections = document.querySelectorAll('section');
let navLinks = document.querySelectorAll('header nav a');
let header = document.querySelector('.header');
let lastScrollY = window.scrollY;

window.onscroll = () => {
    // Header hide/show behavior
    const currentScrollY = window.scrollY;
    if (currentScrollY > lastScrollY) {
        // Scrolling down - hide header
        header.classList.add('header--hidden');
    } else {
        // Scrolling up - show header
        header.classList.remove('header--hidden');
    }
    lastScrollY = currentScrollY;

};

// Mobile Menu Toggle
const menuBtn = document.querySelector('.menu-btn');

if (menuBtn && navbar) {
    menuBtn.addEventListener('click', () => {
        navbar.classList.toggle('active');
        menuBtn.classList.toggle('active');
        // Add/remove body overflow style based on navbar state
        if (navbar.classList.contains('active')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = ''; // Revert to default
        }
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!menuBtn.contains(e.target) && !navbar.contains(e.target)) {
            if (navbar.classList.contains('active')) { // Only act if closing
                navbar.classList.remove('active');
                menuBtn.classList.remove('active');
                document.body.style.overflow = ''; // Restore scroll
            }
        }
    });

    // Close menu when clicking a nav link
    navbar.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            if (navbar.classList.contains('active')) { // Only act if closing
                navbar.classList.remove('active');
                menuBtn.classList.remove('active');
                document.body.style.overflow = ''; // Restore scroll
            }
        });
    });
}

