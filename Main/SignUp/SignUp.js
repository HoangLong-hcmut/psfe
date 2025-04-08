const signUpForm = document.querySelector('.form-box form'); // Target the form within .form-box
const fullnameInput = document.getElementById('fullname');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const confirmPasswordInput = document.getElementById('confirm-password');
const termsCheckbox = document.getElementById('terms');

if (signUpForm) {
    signUpForm.addEventListener('submit', async (event) => {
        event.preventDefault(); // Prevent default form submission

        const fullname = fullnameInput.value;
        const email = emailInput.value;
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        const termsAgreed = termsCheckbox.checked;

        // Basic Client-side Validation (Server-side is primary)
        if (!fullname || !email || !password || !confirmPassword) {
            alert('Please fill in all fields.');
            return;
        }
        if (password !== confirmPassword) {
            alert('Passwords do not match.');
            return;
        }
         if (password.length < 6) { // Mirror backend validation if possible
             alert('Password must be at least 6 characters long.');
             return;
         }
        if (!termsAgreed) {
            alert('You must agree to the Terms of Service and Privacy Policy.');
            return;
        }

        try {
            // Use the full URL to your running Flask backend
            const response = await fetch('http://127.0.0.1:5000/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ fullname, email, password }),
            });

            const result = await response.json();

            if (response.ok || response.status === 201) { // Check for 201 Created status
                console.log('Sign up successful!', result);
                
                // Show success message
                alert('Sign up successful! Redirecting you to login...');
                
                // Clear the form
                signUpForm.reset();
                
                // Add a small delay before redirect for better UX
                setTimeout(() => {
                    window.location.href = '../Login/Login.html';
                }, 1000);
            } else {
                console.error('Sign up failed:', result.message || 'Could not create account');
                 // TODO: Show user-friendly error message in the UI
                alert(`Sign up failed: ${result.message || 'Could not create account'}`);
            }
        } catch (error) {
            console.error('Sign up error during fetch:', error);
             // TODO: Show user-friendly error message in the UI
            alert('An error occurred during sign up. Please check the console and try again.');
        }
    });
} else {
    console.error('Sign up form not found!');
} 