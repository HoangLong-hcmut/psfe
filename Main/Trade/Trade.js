let tradeGridHTML = document.querySelector('.trade-grid');
let listProducts = [];
let currentSearch = '';
let currentSortBy = 'name'; // Default sort by product name
let currentSortOrder = 'asc';
let debounceTimer;

// --- Centralized Fetching and Displaying --- 
const fetchAndDisplayProducts = () => {
    // Build the API URL with query parameters
    let apiUrl = 'http://127.0.0.1:5000/api/trades?';
    const params = [];
    if (currentSearch) {
        params.push(`search=${encodeURIComponent(currentSearch)}`);
    }
    if (currentSortBy) {
        params.push(`sortBy=${encodeURIComponent(currentSortBy)}`);
        params.push(`sortOrder=${encodeURIComponent(currentSortOrder)}`);
    }
    apiUrl += params.join('&');

    // Prepare headers, include Authorization if token exists
    const headers = new Headers();
    const token = localStorage.getItem('authToken');
    if (token) {
        headers.append('Authorization', `Bearer ${token}`);
    }

    fetch(apiUrl, { headers: headers }) // Pass headers to fetch
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            listProducts = data.trades || data; // Adjust based on backend response structure
            addDataToHTML();
        })
        .catch(error => {
            console.error('Error loading trades:', error);
            // Update the correct grid element
            if (tradeGridHTML) {
                tradeGridHTML.innerHTML = '<p class="error-message">Failed to load trades. Please ensure the server is running and try again.</p>';
            }
        });
};

// --- Helper Functions ---

// Function to generate star ratings HTML
const generateStars = (rating) => {
    if (rating === null || rating === undefined || rating < 0 || rating > 5) {
        return '<span class="no-rating">Not rated</span>'; // Or return empty string
    }
    const fullStars = Math.floor(rating);
    const halfStar = rating % 1 >= 0.5 ? 1 : 0;
    const emptyStars = 5 - fullStars - halfStar;
    let starsHTML = '';
    for (let i = 0; i < fullStars; i++) starsHTML += '<i class="bx bxs-star"></i>';
    if (halfStar) starsHTML += '<i class="bx bxs-star-half"></i>';
    for (let i = 0; i < emptyStars; i++) starsHTML += '<i class="bx bx-star"></i>';
    return `<span class="rating-value">(${rating.toFixed(1)})</span> ${starsHTML}`;
};

// Function to show notifications
const showNotification = (message, type = 'success', duration = 5000) => { // Increased default duration
    const notificationArea = document.getElementById('notification-area');
    if (!notificationArea) return;

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;

    // Create message content element
    const messageElement = document.createElement('span');
    messageElement.innerHTML = message; // Use innerHTML to render the link

    // Create close button
    const closeButton = document.createElement('button');
    closeButton.className = 'notification-close-btn';
    closeButton.innerHTML = '&times;'; // 'X' symbol

    // Function to close the notification
    const closeNotification = () => {
        notification.style.opacity = '0';
        // Use transitionend event for smoother removal, or fallback to timeout
        notification.addEventListener('transitionend', () => notification.remove(), { once: true });
        // Fallback timeout in case transitionend doesn't fire (e.g., if transition is interrupted)
        setTimeout(() => notification.remove(), 600); 
    };

    closeButton.addEventListener('click', closeNotification);

    // Append elements
    notification.appendChild(messageElement);
    notification.appendChild(closeButton);
    notificationArea.appendChild(notification);

    // Auto-close notification
    const autoCloseTimeout = setTimeout(closeNotification, duration);

    // Optional: Clear timeout if manually closed
    closeButton.addEventListener('click', () => clearTimeout(autoCloseTimeout));
};

// --- Data Display ---

const addDataToHTML = () => {
    // Use the correct grid selector
    if (!tradeGridHTML) {
        console.error("Trade grid element not found!");
        return;
    }
    tradeGridHTML.innerHTML = '';
    if (listProducts.length > 0) {
        // Get logged-in user info (if available)
        const userInfo = JSON.parse(localStorage.getItem('userInfo'));
        const loggedInUserId = userInfo ? userInfo.id : null;

        listProducts.forEach(product => {
            let newProduct = document.createElement('div');
            newProduct.classList.add('trade-card');
            newProduct.dataset.productId = product.id;

            // Format price safely
            const formattedPrice = typeof product.price === 'number' ? '$' + product.price.toFixed(2) : product.price;
            // Generate average rating stars
            const ratingHTML = generateStars(product.rating);

            // --- Rating Input Logic ---
            let ratingInputHTML = '';
            if (loggedInUserId &&
                product.status === 'completed' &&
                product.seller_id !== loggedInUserId &&
                product.current_user_rating_score === null)
            {
                // User can rate this completed trade
                ratingInputHTML = `
                    <div class="rate-trade-controls" data-trade-id="${product.id}">
                        <span>Rate this trade:</span>
                        <div class="rating-stars-input">
                            <i class='bx bx-star rate-star' data-value="1"></i>
                            <i class='bx bx-star rate-star' data-value="2"></i>
                            <i class='bx bx-star rate-star' data-value="3"></i>
                            <i class='bx bx-star rate-star' data-value="4"></i>
                            <i class='bx bx-star rate-star' data-value="5"></i>
                        </div>
                    </div>
                `;
            } else if (product.current_user_rating_score !== null) {
                 // User has already rated this trade
                 ratingInputHTML = `<div class="already-rated">You rated: ${generateStars(product.current_user_rating_score)}</div>`;
            }
            // --- End Rating Input Logic ---

            newProduct.innerHTML = `
                <img src="${product.image || './Image/placeholder.png'}" alt="${product.name}" class="trade-card-img">
                <div class="card-content">
                    <h3>${product.name}</h3>
                    <div class="card-rating">Avg Rating: ${ratingHTML}</div>
                    ${ratingInputHTML}
                    <p class="price">Unit Price: ${formattedPrice}</p>
                    <p class="quantity-display">Quantity: ${product.quantity}</p>
                    ${product.description ? `<p class="description">${product.description}</p>` : ''}
                    ${product.place ? `<p class="place"><i class='bx bx-map-pin'></i> ${product.place}</p>` : ''}
                    <div class="card-footer">
                         ${product.business_name ? `<span><i class='bx bx-store-alt'></i> ${product.business_name} ${product.seller_average_rating !== null ? '<span class="seller-rating-display">' + generateStars(product.seller_average_rating) + '</span>' : '<span class="no-rating">(Not Rated)</span>'}</span>` : ''}
                         <div class="add-to-cart-controls"> 
                             <input type="number" class="quantity-input" value="1" min="1" max="${product.quantity}" data-product-id="${product.id}">
                             <button type="button" class="add-to-cart-btn" data-product-id="${product.id}">
                                 <i class='bx bx-cart-add'></i> Add to Cart
                             </button>
                         </div>
                    </div>
                </div>
            `;
            tradeGridHTML.appendChild(newProduct);
        });
    } else {
        // Provide feedback when no products match search/filters
        if (currentSearch) {
            tradeGridHTML.innerHTML = '<p>No trades found matching your search.</p>';
        } else {
             tradeGridHTML.innerHTML = '<p>No trades currently available.</p>';
        }
    }

    // --- Add Rating Event Listener ---
    tradeGridHTML.addEventListener('click', (event) => {
        if (event.target.classList.contains('rate-star')) {
             const star = event.target;
             const ratingControls = star.closest('.rate-trade-controls');
             const tradeId = ratingControls?.dataset.tradeId;
             const ratingValue = star.dataset.value;
             const token = localStorage.getItem('authToken');

             if (tradeId && ratingValue && token) {
                // --- Visual Feedback --- 
                const stars = ratingControls.querySelectorAll('.rate-star');
                stars.forEach(s => {
                    s.classList.remove('selected'); // Remove previous selection if any
                    if (parseInt(s.dataset.value) <= parseInt(ratingValue)) {
                        s.classList.add('selected'); // Add selected class up to the clicked star
                    }
                });
                ratingControls.classList.add('disabled'); // Disable further clicks visually
                // --- End Visual Feedback ---

                console.log(`Rating ${ratingValue} clicked for trade ${tradeId}`); 
                submitRating(tradeId, parseInt(ratingValue, 10), token).finally(() => {
                    // Re-enable controls only if the submission fails? 
                    // Currently, fetchAndDisplayProducts() refreshes, so controls are removed anyway on success.
                    // If refresh wasn't happening, you might do: ratingControls.classList.remove('disabled');
                }); 
             } else if (!token) {
                 showNotification('Please log in to rate trades.', 'warning');
             } else {
                console.error("Missing tradeId or ratingValue for rating action.");
             }
        }
    });
    // --- End Rating Event Listener ---
};

// Initial load
const initApp = () => {
   fetchAndDisplayProducts(); // Fetch initial data from server
};

// Make sure DOM is loaded before initApp and attaching listeners
document.addEventListener('DOMContentLoaded', () => {
    // Re-select the grid inside DOMContentLoaded in case it wasn't ready before
    tradeGridHTML = document.querySelector('.trade-grid');
    if (!tradeGridHTML) {
        console.error("Critical: Trade grid element not found on DOMContentLoaded!");
        return; // Stop if grid doesn't exist
    }

    initApp(); // Load initial products

    // --- Search Handling ---
    const searchInput = document.querySelector('.search-input'); // Select the input directly
    const searchBtn = document.querySelector('.search-btn');

    const performSearch = () => {
        clearTimeout(debounceTimer); // Clear previous timer
        const searchValue = searchInput ? searchInput.value.toLowerCase().trim() : '';

        // Use debounce for input, immediate for button click
        debounceTimer = setTimeout(() => {
            if (currentSearch !== searchValue) { // Only fetch if search term changed
                currentSearch = searchValue;
                fetchAndDisplayProducts();
            }
        }, 300); // Debounce for 300ms
    };

    if (searchInput) {
        searchInput.addEventListener('input', performSearch);
    } else {
        console.error("Search input element not found!");
    }
    if (searchBtn) {
        searchBtn.addEventListener('click', () => {
            clearTimeout(debounceTimer); // Cancel any pending input debounce
            currentSearch = searchInput ? searchInput.value.toLowerCase().trim() : '';
            fetchAndDisplayProducts(); // Fetch immediately on button click
        });
    } else {
        console.error("Search button element not found!");
    }


    // --- Sort Handling (Update options) ---
    const sortDropdown = document.querySelector('.sort-dropdown');
    const sortBtn = document.querySelector('.sort-btn');
    const sortMenu = document.querySelector('.sort-menu');

    if (sortDropdown && sortBtn && sortMenu) {
         const sortOptions = sortMenu.querySelectorAll('button');

        sortOptions.forEach(option => {
            option.addEventListener('click', function() {
                const sortType = this.dataset.sort; // e.g., 'name', 'price', 'business_name', 'place'

                // Update sortBy based on button clicked
                // Assuming default 'asc' order
                switch(sortType) {
                    case 'name':
                        currentSortBy = 'name';
                        break;
                    case 'price':
                        currentSortBy = 'price';
                        break;
                    case 'business_name': // Match backend parameter
                         currentSortBy = 'business_name';
                         break;
                    case 'place': // Added sort by place
                        currentSortBy = 'place';
                        break;
                    default:
                         currentSortBy = 'name';
                         break;
                }
                currentSortOrder = 'asc'; // Reset to asc for simplicity, or implement toggle

                sortDropdown.classList.remove('active');
                fetchAndDisplayProducts();
            });
        });

        // Toggle dropdown visibility
        sortBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent click from immediately closing dropdown
            sortDropdown.classList.toggle('active');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!sortDropdown.contains(e.target)) {
                sortDropdown.classList.remove('active');
            }
        });

    } else {
        console.error("Sort elements not found!");
    }


    // --- Add Product Handling (Include description and place) ---
    const addTradeForm = document.getElementById('add-trade-form');
    if (addTradeForm) {
        addTradeForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            // Get data from the form
            const name = document.getElementById('product-name')?.value;
            const price = document.getElementById('product-price')?.value;
            const image = document.getElementById('product-image')?.value;
            const description = document.getElementById('product-description')?.value;
            const place = document.getElementById('product-place')?.value;
            const quantityInput = document.getElementById('product-quantity');
            let quantity = 1; // Default quantity
            if (quantityInput) {
                const parsedQuantity = parseInt(quantityInput.value, 10);
                if (!isNaN(parsedQuantity) && parsedQuantity >= 1) {
                    quantity = parsedQuantity;
                }
            }

            // Validate required fields
            if (!name || !price) {
                showNotification('Product Name and Price are required.', 'error');
                return;
            }

            // Validate price format (simple check)
            if (isNaN(parseFloat(price))) {
                 showNotification('Invalid Price format. Please enter a number.', 'error');
                 return;
            }

            const tradeData = {
                name,
                price: parseFloat(price), // Ensure price is a number
                image: image || null, // Send null if empty
                description: description || null,
                place: place || null,
                quantity: quantity // Add quantity to the data payload
            };

            const token = localStorage.getItem('authToken');
            if (!token) {
                alert('You must be logged in to add a trade.');
                return;
            }

            try {
                const response = await fetch('http://127.0.0.1:5000/api/trades', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(tradeData)
                });

                if (!response.ok) {
                     let errorData;
                     try {
                         errorData = await response.json();
                     } catch (jsonError) {
                         throw new Error(`HTTP error ${response.status}`);
                     }
                     throw new Error(errorData.message || `Network response was not ok (${response.status})`);
                }

                fetchAndDisplayProducts();
                addTradeForm.reset();
                alert('Your trade item has been added successfully!');

            } catch (error) {
                console.error('Error adding trade:', error);
                alert(`Failed to add trade: ${error.message}.`);
            }
        });
    } else {
         console.error("Add trade form element not found!");
    }

    // --- Export CSV Button Handler (New) ---
    const exportBtn = document.getElementById('export-csv-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            // Construct the full URL for the export endpoint
            const exportUrl = 'http://127.0.0.1:5000/api/trades/export';
            // Trigger download by navigating to the URL
            window.location.href = exportUrl;
        });
    } else {
        console.error("Export CSV button not found!");
    }

    // --- Header Scroll Behavior (Keep as is or adapt if needed) ---
    const header = document.querySelector('.header');
    if (header) {
        let lastScrollY = window.scrollY;
        window.addEventListener('scroll', () => {
             const currentScrollY = window.scrollY;
            if (currentScrollY > lastScrollY && currentScrollY > header.offsetHeight) {
                header.classList.add('header--hidden');
            } else {
                header.classList.remove('header--hidden');
            }
            lastScrollY = currentScrollY <= 0 ? 0 : currentScrollY;
        });
    } else {
        console.warn("Header element not found for scroll behavior.");
    }

    // --- Event Delegation for Add to Cart --- 
    if (tradeGridHTML) {
        tradeGridHTML.addEventListener('click', (event) => {
            // Check if the clicked element is an add-to-cart button
            if (event.target.closest('.add-to-cart-btn')) {
                event.preventDefault(); // Prevent any default button behavior
                event.stopPropagation(); // Stop the event from bubbling up
                const button = event.target.closest('.add-to-cart-btn');
                const tradeId = button.dataset.productId;
                
                // Find the corresponding quantity input
                const controlsWrapper = button.closest('.add-to-cart-controls');
                const quantityInput = controlsWrapper ? controlsWrapper.querySelector('.quantity-input') : null;
                const quantity = quantityInput ? parseInt(quantityInput.value, 10) : 1;

                if (tradeId && quantity > 0) {
                    addToCartHandler(parseInt(tradeId, 10), quantity);
                } else {
                    console.error("Could not get trade ID or valid quantity for cart action.");
                }
            }
            // Add more delegated events here if needed (e.g., for rating clicks)
        });
    } else {
        console.error("Trade grid not found, cannot attach cart listener.");
    }

}); // End of DOMContentLoaded

// Add to Cart Handler
const addToCartHandler = async (tradeId, quantity) => {
    const token = localStorage.getItem('authToken');
    if (!token) {
        showNotification('Please log in to add items to your cart.', 'error');
        return;
    }

    // Get logged in user ID
    const userInfo = JSON.parse(localStorage.getItem('userInfo'));
    const loggedInUserId = userInfo ? userInfo.id : null;

    // Find product details, including seller_id and available quantity
    const product = listProducts.find(p => p.id === tradeId);

    if (!product) {
        showNotification('Product details not found. Cannot add to cart.', 'error');
        console.error(`Product with ID ${tradeId} not found in listProducts.`);
        return;
    }

    // --- Check if requested quantity exceeds available quantity --- 
    if (quantity > product.quantity) {
        showNotification(`You cannot add more items than available (Available: ${product.quantity}).`, 'warning');
        return; 
    }
    // --- End quantity check ---

    // --- Prevent seller from adding own item --- 
    if (loggedInUserId && product.seller_id === loggedInUserId) {
        showNotification('You cannot add your own listing to the cart.', 'warning');
        return;
    }
    // --- End prevention check --- 

    const productName = product.name || 'Item'; // Fallback name

    try {
        const response = await fetch('http://127.0.0.1:5000/api/cart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ trade_id: tradeId, quantity: quantity })
        });

        const result = await response.json();

        if (response.ok) {
            // Construct detailed success message
            const successMessage = `Added ${quantity} x <strong>${productName}</strong> to cart! <a href="../Profile/Profile.html">View Cart</a>`;
            showNotification(successMessage, 'success');
        } else {
            throw new Error(result.message || `Failed to add item (${response.status})`);
        }
    } catch (error) {
        console.error('Error adding to cart:', error);
        showNotification(`Error: ${error.message}`, 'error');
    }
};

// --- Add submitRating function (adapted from Profile.js) ---
async function submitRating(tradeId, ratingValue, token) {
    // Maybe add a loading indicator near the stars?
    console.log(`Submitting rating: ${ratingValue} for trade ID: ${tradeId}`); 
    try {
        const response = await fetch(`http://127.0.0.1:5000/api/trades/${tradeId}/rate`, { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ rating_score: ratingValue }) 
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `Failed to submit rating (${response.status})`);
        }
        const result = await response.json();
        console.log(`Rating submitted for ${tradeId}:`, result.message);
        showNotification('Rating submitted successfully!', 'success');
        // Refresh product data to show updated average and remove rating input
        fetchAndDisplayProducts(); 

    } catch (error) {
        console.error('Error submitting rating:', error);
        showNotification(`Error submitting rating: ${error.message}`, 'error');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const addNewTradeBtn = document.getElementById('add-new-trade-btn'); // Button to open the form
    const addTradeFormContainer = document.getElementById('add-trade-form-container'); // Form container

    if (addNewTradeBtn && addTradeFormContainer) {
        addNewTradeBtn.addEventListener('click', () => {
            // Toggle the 'hidden' and 'visible' classes
            if (addTradeFormContainer.classList.contains('hidden')) {
                addTradeFormContainer.classList.remove('hidden');
                addTradeFormContainer.classList.add('visible');
            } else {
                addTradeFormContainer.classList.remove('visible');
                addTradeFormContainer.classList.add('hidden');
            }
        });
    } else {
        console.error("Add New Trade button or form container not found!");
    }
});

function toggleForm() {
    const div = document.getElementById("formHidden") || document.getElementById("formVisible");

    if (div.style.display === "none") {
      div.style.display = "flex";
      div.id = "formVisible";
    } else {
      div.style.display = "none";
      div.id = "formHidden";
    }
  }


  const container = document.querySelector('.container');
const LoginLink = document.querySelector('.SignInLink');
const RegisterLink = document.querySelector('.SignUpLink');

if (RegisterLink && container) {
    RegisterLink.addEventListener('click', () => {
        container.classList.add('active');
    });
}

if (LoginLink && container) {
    LoginLink.addEventListener('click', () => {
        container.classList.remove('active');
    });
}

// --- Added Form Submission Logic ---
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
            // Use the full URL to your running Flask backend
            const response = await fetch('http://127.0.0.1:5000/api/login', {
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


