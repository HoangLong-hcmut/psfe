const loginForm = document.querySelector('.form-box form'); // Target the form within .form-box
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');

if (loginForm) {
    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault(); // Prevent default form submission

        const username = usernameInput.value;
        const password = passwordInput.value;

        // Basic client-side check
        if (!username || !password) {
            console.error('Login Error: Please enter both username (email) and password.');
            // TODO: Show user-friendly message in the UI
            alert('Please enter both username (email) and password.');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }), // 'username' field holds email
            });

            const result = await response.json();

            if (response.ok && result.token) {
                console.log('Login successful!', result);
                // --- Store the JWT in localStorage ---
                localStorage.setItem('authToken', result.token);
                // Optionally store user info too, but token is key
                if(result.user) {
                    localStorage.setItem('userInfo', JSON.stringify(result.user));
                }

                // --- Redirect to a protected page (e.g., profile) ---
                // You'll need to create profile.html
                window.location.href = '../Profile/profile.html'; // Adjust path if needed
            } else {
                console.error('Login failed:', result.message || 'Invalid credentials');
                 // TODO: Show user-friendly error message in the UI
                alert(`Login failed: ${result.message || 'Invalid credentials'}`);
            }
        } catch (error) {
            console.error('Login error during fetch:', error);
             // TODO: Show user-friendly error message in the UI
            alert('An error occurred during login. Please check the console and try again.');
        }
    });
} else {
    console.error('Login form not found!');
}

// Mobile Menu Toggle
const menuBtn = document.querySelector('.menu-btn');
const navbar = document.querySelector('.navbar');

if (menuBtn && navbar) {
    menuBtn.addEventListener('click', () => {
        navbar.classList.toggle('active');
        menuBtn.classList.toggle('active');
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!menuBtn.contains(e.target) && !navbar.contains(e.target)) {
            navbar.classList.remove('active');
            menuBtn.classList.remove('active');
        }
    });

    // Close menu when clicking a nav link
    navbar.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            navbar.classList.remove('active');
            menuBtn.classList.remove('active');
        });
    });
}