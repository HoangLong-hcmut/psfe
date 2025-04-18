document.addEventListener('DOMContentLoaded', () => {
    // --- Header Scroll Behavior (Moved from HTML) ---
    let lastScroll = 0;
    const header = document.querySelector('header');
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        if (!header) return;
        if (currentScroll <= 0) {
            header.classList.remove('header--hidden');
        } else if (currentScroll > lastScroll) {
            header.classList.add('header--hidden');
        } else {
            header.classList.remove('header--hidden');
        }
        lastScroll = currentScroll;
    });

    // --- Page Elements ---
    const contactForm = document.getElementById('contactForm');
    const loginPromptMessage = document.getElementById('login-prompt-message');
    const exportBtn = document.getElementById('export-contacts-btn');
    
    // --- Check Login Status (Moved from HTML) ---
    const token = localStorage.getItem('authToken');

    if (token) {
        // User IS logged in
        console.log("Contact.js: User is logged in.");
        if (contactForm) {
            contactForm.style.display = 'block';
        }
        if (loginPromptMessage) {
            loginPromptMessage.style.display = 'none';
        }

        // Add form submission listener only if logged in
        if (contactForm) {
             contactForm.addEventListener('submit', async (event) => {
                event.preventDefault(); // Prevent default form submission

                const formData = {
                    name: document.getElementById('name').value,
                    email: document.getElementById('email').value,
                    subject: document.getElementById('subject').value,
                    message: document.getElementById('message').value
                };

                // Simple validation
                if (!formData.name || !formData.email || !formData.message) {
                    alert('Please fill in all required fields (Name, Email, Message).');
                    return;
                }
                if (!formData.email.includes('@') || !formData.email.includes('.')) {
                    alert('Please enter a valid email address.');
                    return;
                }

                try {
                    const response = await fetch(`${API_BASE_URL}/api/contact`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}` // Token is available here
                        },
                        body: JSON.stringify(formData)
                    });

                    const responseText = await response.text(); // Get raw response text

                    // Now try to parse the text as JSON
                    if (response.ok) {
                        try {
                            const result = JSON.parse(responseText); // Parse the text we got
                            alert(`Message sent successfully!`);
                            contactForm.reset();
                        } catch (parseError) {
                            console.error('Error parsing JSON response:', parseError, 'Raw text:', responseText);
                            alert('Message sent, but received an unexpected response format from the server.');
                        }
                    } else {
                         // Attempt to parse error response as JSON, but handle failure
                         let result = { message: responseText }; // Default to raw text
                         try {
                            result = JSON.parse(responseText); // Try parsing error response
                         } catch (parseError) {
                            console.warn('Could not parse error response as JSON. Raw text:', responseText);
                         }

                         if (response.status === 401) {
                            alert('Authentication failed. Your session might have expired. Please log in again.');
                        } else {
                            // Use parsed message if available, otherwise use raw text or status
                            alert(`Failed to send message: ${result.message || response.statusText || 'Unknown error'}`);
                        }
                    }
                } catch (error) {
                    console.error('Error submitting contact form:', error);
                    alert('An error occurred while sending the message. Please try again later.');
                }
            });
        } else {
            console.log("Contact.js: Contact form not found.");
        }

        // Export button listener for logged-in users (moved inside token check)
        if (exportBtn) {
            exportBtn.addEventListener('click', async () => {
                const exportToken = localStorage.getItem('authToken'); // Re-check token just in case
                if (!exportToken) {
                    alert('Authentication error. Please log in again.');
                    return;
                }

                try {
                    const response = await fetch(`${API_BASE_URL}/api/contacts/export`, {
                        method: 'GET',
                        headers: {
                            'Authorization': `Bearer ${exportToken}`
                        }
                    });


                    if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        // Extract filename from content-disposition header if available, otherwise default
                        const disposition = response.headers.get('content-disposition');
                        let filename = 'contacts_export.csv'; // Default filename
                        if (disposition && disposition.indexOf('attachment') !== -1) {
                            const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                            const matches = filenameRegex.exec(disposition);
                            if (matches != null && matches[1]) {
                                filename = matches[1].replace(/['"]/g, '');
                            }
                        }
                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        a.remove();
                        console.log("File download initiated as:", filename);
                    } else {
                        // Handle non-OK responses (like 401, 403, 500 etc.)
                        const errorData = await response.json().catch(() => ({ message: 'Failed to parse error response.' })); // Try to get error message
                        console.error('Export failed:', response.status, errorData);
                        alert(`Failed to export contacts: ${response.status} - ${errorData.message || 'Unknown error'}`);
                         if (response.status === 401) {
                             alert('Authentication failed. Your session might have expired. Please log in again.');
                             // Optionally redirect
                         }
                    }
                } catch (error) {
                    console.error('Error during contacts export fetch:', error);
                    alert('An error occurred while exporting contacts. Please check the console and try again.');
                }
            });
        } else {
            console.log("Contact.js: Export button not found (logged in check).");
        }

    } else {
        // User is NOT logged in
        console.log("Contact.js: User is not logged in.");
        if (contactForm) {
            contactForm.style.display = 'none';
        }
        if (loginPromptMessage) {
            loginPromptMessage.style.display = 'block';
        }

        // Export button listener for logged-out users
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                alert('Please log in to export contacts.');
            });
        } else {
             console.log("Contact.js: Export button not found (logged out check).");
        }
    }
}); 