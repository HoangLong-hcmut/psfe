let menuIcon = document.querySelector('#menu-icon');
let navbar = document.querySelector('.navbar');
let sections = document.querySelectorAll('section');
let navLinks = document.querySelectorAll('header nav a');
let header = document.querySelector('.header');
let lastScrollY = window.scrollY;
let homeLink = document.querySelector('header nav a[href="/"]');

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

    // Keep home link active
    homeLink.classList.add('active');
};

menuIcon.onclick = () => {
    menuIcon.classList.toggle('bx-x');
    navbar.classList.toggle('active');
};