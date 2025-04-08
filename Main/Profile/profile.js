document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('authToken');

    // --- Element References ---
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error');
    const profileActionsDiv = document.getElementById('profile-actions');
    const logoutButton = document.getElementById('logout-button');
    // Header elements
    const profileFullname = document.getElementById('profile-fullname');
    const profileEmail = document.getElementById('profile-email');
    // Stats elements
    const listingsCountEl = document.getElementById('stats-listings-count');
    const successfulTradesEl = document.getElementById('stats-successful-trades');
    const averageRatingEl = document.getElementById('stats-average-rating');
    // Content Containers
    const cartContainer = document.getElementById('cart-items-container');
    const listingsContainer = document.getElementById('listings-container');
    const incomingOrdersContainer = document.getElementById('incoming-orders-container');
    // Section references (to show/hide)
    const cartSection = document.querySelector('.profile-cart');
    const listingsSection = document.querySelector('.profile-listings');
    const incomingOrdersSection = document.querySelector('.profile-incoming-orders');
    const statsSection = document.querySelector('.profile-stats');

    // --- Initial State ---
    loadingDiv.style.display = 'block'; // Show loading initially
    errorDiv.textContent = '';
    // Hide content sections until data is loaded or guest view is confirmed
    if (cartSection) cartSection.style.display = 'none';
    if (listingsSection) listingsSection.style.display = 'none';
    if (incomingOrdersSection) incomingOrdersSection.style.display = 'none';
    if (statsSection) statsSection.style.display = 'none';
    if (profileActionsDiv) profileActionsDiv.style.display = 'none';

    // --- Logic based on login state ---
    if (token) {
        console.log("Token found, fetching profile data...");
        fetchProfileData(token);
        if (profileActionsDiv) profileActionsDiv.style.display = 'block'; // Show logout/edit

        if (logoutButton) {
            logoutButton.addEventListener('click', () => {
                localStorage.removeItem('authToken');
                localStorage.removeItem('userInfo'); // Also remove cached user info if present
                alert('You have been logged out.');
                window.location.href = '../Login/Login.html';
            });
        } else {
            console.error("Logout button not found!");
        }
    } else {
        console.log("No token found, showing guest view elements...");
        loadingDiv.style.display = 'none';
        // Show a message or redirect for guests
        if (profileFullname) profileFullname.textContent = 'Guest';
        if (profileEmail) profileEmail.textContent = 'Please log in to view your profile.';
        // Optionally hide stats/cart/listings for guests or show a prompt
        if (statsSection) statsSection.style.display = 'none';
        if (cartSection) cartSection.style.display = 'none';
        if (listingsSection) listingsSection.style.display = 'none';
        if (incomingOrdersSection) incomingOrdersSection.style.display = 'none';
        // Show a link to log in
        errorDiv.innerHTML = 'Welcome, Guest! Please <a href="../Login/Login.html">login</a> or <a href="../SignUp/SignUp.html">sign up</a>.';
    }

    // --- Event Delegation for Cart Removal ---
    if (cartContainer) {
        cartContainer.addEventListener('click', async (event) => {
            const currentToken = localStorage.getItem('authToken'); // Re-get token
            if (!currentToken) return;

            if (event.target.closest('.remove-cart-item-btn')) {
                const button = event.target.closest('.remove-cart-item-btn');
                const tradeId = button.dataset.tradeId;
                if (tradeId) {
                    await removeCartItem(tradeId, currentToken);
                    await fetchCartData(currentToken); // Refresh cart
                }
            } else if (event.target.closest('.initiate-purchase-btn')) {
                 const button = event.target.closest('.initiate-purchase-btn');
                 const tradeId = button.dataset.tradeId;
                 const cartItemCard = button.closest('.cart-item-card');
                 const itemName = cartItemCard?.querySelector('.cart-item-details h5')?.textContent || 'the item';
                 const sellerName = cartItemCard?.querySelector('.cart-item-details p:last-of-type')?.textContent.replace('Seller: ', '') || 'the seller';

                 // Show notification instead of alert
                 const message = `We have informed <strong>${sellerName}</strong> about your interest in <strong>${itemName}</strong> (Trade ID: ${tradeId}).`;
                 showNotification(message, 'info'); // Use 'info' type or 'success'
                 
                 // Optional: Add backend call here later to actually send a notification
            }
            // --- Handle Order Button Click --- 
            else if (event.target.closest('.order-btn')) {
                const button = event.target.closest('.order-btn');
                const tradeId = button.dataset.tradeId;
                if (tradeId) {
                    await orderItem(tradeId, currentToken);
                }
            }
        });
    }

    // Event Delegation for Listings Container
    if (listingsContainer) {
        listingsContainer.addEventListener('click', async (event) => {
            const token = localStorage.getItem('authToken'); // Get token inside handler
            if (!token) return; // Need to be logged in for actions

            // Handle Remove Listing clicks
            if (event.target.closest('.remove-listing-btn')) {
                const button = event.target.closest('.remove-listing-btn');
                const tradeId = button.dataset.tradeId;
                // Confirmation dialog
                if (tradeId && confirm('Are you sure you want to permanently remove this listing?')) {
                    await removeListing(tradeId, token);
                }
            }
            // Handle Rating Star clicks
            else if (event.target.classList.contains('rate-star')) {
                 const star = event.target;
                 const ratingControls = star.closest('.rate-trade-controls');
                 const tradeId = ratingControls?.dataset.tradeId;
                 const ratingValue = star.dataset.value;

                 if (tradeId && ratingValue) {
                    // Optional: Add visual feedback (highlight selected stars) here if desired
                    console.log(`Rating ${ratingValue} clicked for trade ${tradeId}`); // Debug log
                    await submitRating(tradeId, parseInt(ratingValue, 10), token);
                 } else {
                    console.error("Missing tradeId or ratingValue for rating action.");
                 }
            }
        });
    }

    // --- Event Delegation for Incoming Orders Actions --- 
    if (incomingOrdersContainer) {
        incomingOrdersContainer.addEventListener('click', async (event) => {
            const token = localStorage.getItem('authToken');
            if (!token) return;

            const acceptButton = event.target.closest('.accept-order-btn');
            const declineButton = event.target.closest('.decline-order-btn');

            if (acceptButton) {
                const cartItemId = acceptButton.dataset.cartItemId;
                if (cartItemId && confirm('Are you sure you want to accept this order? This will mark the order as completed and decrease stock.')) {
                    await acceptIncomingOrder(cartItemId, token);
                }
            } else if (declineButton) {
                const cartItemId = declineButton.dataset.cartItemId;
                if (cartItemId && confirm('Are you sure you want to decline this order? The buyer will be notified.')) {
                    await declineIncomingOrder(cartItemId, token);
                }
            }
        });
    }
});

// --- Helper Functions ---

// Function to generate star ratings HTML (copied from Trade.js)
const generateStars = (rating) => {
    if (rating === null || rating === undefined || rating < 0 || rating > 5) {
        return '<span class="no-rating">Not rated</span>';
    }
    const fullStars = Math.floor(rating);
    const halfStar = rating % 1 >= 0.5 ? 1 : 0;
    const emptyStars = 5 - fullStars - halfStar;
    let starsHTML = '';
    for (let i = 0; i < fullStars; i++) starsHTML += '<i class="bx bxs-star"></i>';
    if (halfStar) starsHTML += '<i class="bx bxs-star-half"></i>';
    for (let i = 0; i < emptyStars; i++) starsHTML += '<i class="bx bx-star"></i>';
    // Add numeric value next to stars
    return `<span class="rating-value">(${rating.toFixed(1)})</span> ${starsHTML}`;
};

// Function to show notifications (Copied from Trade.js)
const showNotification = (message, type = 'success', duration = 5000) => {
    // Need a notification area in Profile.html
    let notificationArea = document.getElementById('notification-area'); 
    if (!notificationArea) {
        console.warn("Notification area not found in Profile.html. Adding one dynamically.");
        // Create it if it doesn't exist (basic implementation)
        const container = document.querySelector('.container') || document.body;
        const newArea = document.createElement('div');
        newArea.id = 'notification-area';
        // Add basic styles - ideally these should be in CSS
        newArea.style.position = 'fixed';
        newArea.style.top = '20px';
        newArea.style.right = '20px';
        newArea.style.zIndex = '1000';
        container.appendChild(newArea);
        notificationArea = newArea; // Assign the newly created area
    }

    const notification = document.createElement('div');
    // Basic notification styling - should be in CSS
    notification.style.backgroundColor = type === 'error' ? '#f8d7da' : (type === 'warning' ? '#fff3cd' : '#d4edda');
    notification.style.color = type === 'error' ? '#721c24' : (type === 'warning' ? '#856404' : '#155724');
    notification.style.padding = '15px';
    notification.style.marginBottom = '10px';
    notification.style.border = '1px solid transparent';
    notification.style.borderRadius = '4px';
    notification.style.opacity = '1';
    notification.style.transition = 'opacity 0.5s ease';
    notification.style.display = 'flex';
    notification.style.justifyContent = 'space-between';
    notification.style.alignItems = 'center';
    // Add class for more specific CSS targeting if available
    notification.className = `notification ${type}`;

    const messageElement = document.createElement('span');
    messageElement.innerHTML = message; 

    const closeButton = document.createElement('button');
    closeButton.innerHTML = '&times;'; 
    // Basic close button styling
    closeButton.style.background = 'none';
    closeButton.style.border = 'none';
    closeButton.style.fontSize = '1.2em';
    closeButton.style.cursor = 'pointer';
    closeButton.style.marginLeft = '15px';
    closeButton.className = 'notification-close-btn';

    const closeNotification = () => {
        notification.style.opacity = '0';
        notification.addEventListener('transitionend', () => notification.remove(), { once: true });
        setTimeout(() => notification.remove(), 600); 
    };

    closeButton.addEventListener('click', closeNotification);

    notification.appendChild(messageElement);
    notification.appendChild(closeButton);
    notificationArea.appendChild(notification);

    const autoCloseTimeout = setTimeout(closeNotification, duration);
    closeButton.addEventListener('click', () => clearTimeout(autoCloseTimeout));
};

// --- Data Fetching Functions ---

async function fetchProfileData(token) {
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error');
    const profileFullname = document.getElementById('profile-fullname');
    const profileEmail = document.getElementById('profile-email');
    const listingsContainer = document.getElementById('listings-container');
    const listingsCountEl = document.getElementById('stats-listings-count');
    const successfulTradesEl = document.getElementById('stats-successful-trades');
    const averageRatingEl = document.getElementById('stats-average-rating');
    const statsSection = document.querySelector('.profile-stats');
    const listingsSection = document.querySelector('.profile-listings');
    const successfulTradesLabel = document.getElementById('stats-successful-trades')?.previousElementSibling;

    loadingDiv.style.display = 'block'; // Ensure loading is visible
    errorDiv.textContent = '';

    try {
        // Fetch basic user info (if needed, e.g., from localStorage or a dedicated endpoint)
        const userInfo = JSON.parse(localStorage.getItem('userInfo'));
        if (userInfo) {
            if (profileFullname) profileFullname.textContent = userInfo.fullname;
            if (profileEmail) profileEmail.textContent = userInfo.email;
        } else {
             // If not in localStorage, might need another fetch, but let's assume it is for now
             console.warn("User info not found in localStorage.");
        }

        // Fetch stats and listings
        const statsResponse = await fetch('http://127.0.0.1:5000/api/profile/stats', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!statsResponse.ok) {
            const errorData = await statsResponse.json();
            throw new Error(errorData.message || `Failed to fetch profile stats (${statsResponse.status})`);
        }
        const statsData = await statsResponse.json();

        // Populate Stats
        if (statsSection) statsSection.style.display = 'flex'; // Show stats section
        if (listingsCountEl) listingsCountEl.textContent = statsData.listings.length;

        if (successfulTradesLabel) successfulTradesLabel.textContent = "Success Rate";
        if (statsData.successful_trades_percentage !== undefined) {
            if (successfulTradesEl) successfulTradesEl.textContent = `${statsData.successful_trades_percentage}%`;
        } else {
            if (successfulTradesEl) successfulTradesEl.textContent = 'N/A';
        }

        if (statsData.seller_average_rating !== null) {
            if (averageRatingEl) averageRatingEl.innerHTML = generateStars(statsData.seller_average_rating);
        } else {
            if (averageRatingEl) averageRatingEl.innerHTML = '<span class="no-rating">Not Rated Yet</span>';
        }

        // Populate Listings
        if (listingsSection) listingsSection.style.display = 'block';
        renderListings(statsData.listings);

        // Fetch Cart Data (called separately now)
        await fetchCartData(token);

        // Fetch Incoming Orders Data (New)
        await fetchIncomingOrders(token);

    } catch (error) {
        console.error('Error fetching profile data:', error);
        if (errorDiv) errorDiv.textContent = `Error: ${error.message}. Please try reloading.`;
    } finally {
        if (loadingDiv) loadingDiv.style.display = 'none'; // Hide loading
    }
}

async function fetchCartData(token) {
    const cartContainer = document.getElementById('cart-items-container');
    const cartSection = document.querySelector('.profile-cart');

    try {
        const cartResponse = await fetch('http://127.0.0.1:5000/api/cart', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!cartResponse.ok) {
            const errorData = await cartResponse.json();
            throw new Error(errorData.message || `Failed to fetch cart (${cartResponse.status})`);
        }
        const cartData = await cartResponse.json();

        // Populate Cart
        if (cartSection) cartSection.style.display = 'block';
        renderCart(cartData.cart || []);

    } catch (error) {
        console.error('Error fetching cart data:', error);
        // Optionally display a specific error for the cart
        if (cartContainer) cartContainer.innerHTML = `<p class="error-message">Could not load cart: ${error.message}</p>`;
        // Don't overwrite the main profile error if cart fails
    }
}

// --- New Function to Fetch Incoming Orders ---
async function fetchIncomingOrders(token) {
    const incomingOrdersContainer = document.getElementById('incoming-orders-container');
    const incomingOrdersSection = document.querySelector('.profile-incoming-orders');

    try {
        const response = await fetch('http://127.0.0.1:5000/api/profile/incoming_orders', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `Failed to fetch incoming orders (${response.status})`);
        }
        const data = await response.json();

        // Populate Incoming Orders
        if (incomingOrdersSection) incomingOrdersSection.style.display = 'block';
        renderIncomingOrders(data.incoming_orders || []);

    } catch (error) {
        console.error('Error fetching incoming orders:', error);
        if (incomingOrdersContainer) incomingOrdersContainer.innerHTML = `<p class="error-message">Could not load incoming orders: ${error.message}</p>`;
    }
}

// --- Rendering Functions ---

function renderListings(listings) {
    const listingsContainer = document.getElementById('listings-container');
    if (!listingsContainer) return;

    listingsContainer.innerHTML = ''; // Clear previous listings

    if (!listings || listings.length === 0) {
        listingsContainer.innerHTML = '<p>You haven\'t listed any items yet.</p>';
        return;
    }

    listings.forEach(item => {
        const card = document.createElement('div');
        card.className = 'listing-card'; // Use a class for styling
        const formattedPrice = typeof item.price === 'number' ? '$' + item.price.toFixed(2) : item.price;
        const listedDate = new Date(item.created_at).toLocaleDateString();
        const productRatingHTML = item.average_product_rating !== null ? generateStars(item.average_product_rating) : '<span class="no-rating">Not Rated</span>';

        card.innerHTML = `
            <img src="${item.image || '../Image/placeholder.png'}" alt="${item.name}">
            <div class="listing-details">
                <h5>${item.name}</h5>
                <p>Price: ${formattedPrice}</p>
                <p class="quantity-display">Quantity: ${item.quantity}</p>
                <p>Status: <span class="status-badge status-${item.status || 'unknown'}">${item.status || 'N/A'}</span></p>
                <p>Listed: ${listedDate}</p>
                <p>Avg. Rating: ${productRatingHTML}</p>
                ${item.description ? `<p class="description">Desc: ${item.description}</p>` : ''}
                ${item.place ? `<p class="place"><i class='bx bx-map-pin'></i> ${item.place}</p>` : ''}
                <!-- Action Button: Remove Listing -->
                <button class="remove-listing-btn" data-trade-id="${item.id}" title="Remove this listing"><i class='bx bx-trash'></i> Remove Listing</button>
            </div>
        `;
        listingsContainer.appendChild(card);
    });
}

function renderCart(cartItems) {
    const cartContainer = document.getElementById('cart-items-container');
    if (!cartContainer) return;

    if (!cartItems || cartItems.length === 0) {
        cartContainer.innerHTML = '<p>Your cart is empty.</p>';
        return;
    }

    cartContainer.innerHTML = ''; // Clear previous
    let total = 0;
    cartItems.forEach(item => {
        const card = document.createElement('div');
        card.className = 'cart-item-card';
        const formattedPrice = typeof item.price === 'number' ? '$' + item.price.toFixed(2) : item.price;
        const itemTotal = typeof item.price === 'number' ? item.price * item.quantity : 0;
        total += itemTotal;
        const sellerEmailHTML = item.seller_email ? `<a href="mailto:${item.seller_email}">${item.seller_email}</a>` : 'Email not available';

        // Show Order button only if status is 'pending'
        // Use cart_status which comes from cart_items table
        const orderButtonHTML = item.cart_status === 'pending' ? 
            `<button class="order-btn action-btn" data-trade-id="${item.id}" title="Place Order"><i class='bx bx-check-shield'></i> Order</button>` : '';
        
        // Display different indicator/actions based on cart_status
        let statusIndicatorHTML = '';
        if (item.cart_status === 'ordered') {
             statusIndicatorHTML = '<span class="status-badge status-ordered">Ordered</span>';
        } else if (item.cart_status === 'completed') {
            statusIndicatorHTML = '<span class="status-badge status-completed">Completed</span>';
        } else if (item.cart_status === 'cancelled') {
            statusIndicatorHTML = '<span class="status-badge status-cancelled">Cancelled</span>';
        }

        card.innerHTML = `
            <img src="${item.image || '../Image/placeholder.png'}" alt="${item.name}" class="cart-item-img">
            <div class="cart-item-details">
                <h5>${item.name}</h5>
                <p>Price: ${formattedPrice}</p>
                <p>Quantity: ${item.quantity}</p>
                <p>Seller: ${item.business_name || 'N/A'} (${sellerEmailHTML})</p>
                <p>Cart Status: ${statusIndicatorHTML || '<span class="status-badge status-pending">Pending</span>'}</p> 
            </div>
            <div class="cart-item-actions">
                 <p>Subtotal: $${itemTotal.toFixed(2)}</p>
                 ${orderButtonHTML} 
                 <button class="remove-cart-item-btn action-btn" data-trade-id="${item.id}" title="Remove from Cart"><i class='bx bx-trash'></i> Remove</button>
            </div>
        `;
        cartContainer.appendChild(card);
    });

    // Add Total Price
    const totalElement = document.createElement('div');
    totalElement.className = 'cart-total';
    totalElement.innerHTML = `<h4>Total Cart Price: $${total.toFixed(2)}</h4>`;
    cartContainer.appendChild(totalElement);
}

// --- Updated Function to Render Incoming Orders ---
function renderIncomingOrders(orders) {
    const container = document.getElementById('incoming-orders-container');
    if (!container) return;

    container.innerHTML = ''; // Clear previous items

    if (!orders || orders.length === 0) {
        container.innerHTML = '<p>You have no incoming orders.</p>';
        return;
    }

    orders.forEach(item => {
        const card = document.createElement('div');
        card.className = 'listing-card incoming-order-card'; 
        // Use correct property names from backend query
        const formattedPrice = typeof item.trade_price === 'number' ? '$' + item.trade_price.toFixed(2) : item.trade_price;
        const orderedDate = new Date(item.ordered_at).toLocaleString(); // Use ordered_at for date

        // Add Accept/Decline buttons with cart_item_id
        const actionButtonsHTML = `
            <div class="incoming-order-actions">
                <button class="accept-order-btn action-btn" data-cart-item-id="${item.cart_item_id}" title="Accept Order (Mark as Completed)"><i class='bx bx-check-circle'></i> Accept</button>
                <button class="decline-order-btn action-btn" data-cart-item-id="${item.cart_item_id}" title="Decline Order (Mark as Cancelled)"><i class='bx bx-x-circle'></i> Decline</button>
            </div>
        `;

        card.innerHTML = `
            <img src="${item.trade_image || '../Image/placeholder.png'}" alt="${item.trade_name}">
            <div class="listing-details">
                <h5>${item.trade_name}</h5>
                <p>Price: ${formattedPrice}</p>
                <p>Quantity Ordered: ${item.ordered_quantity}</p>
                <p>Ordered By: ${item.buyer_fullname} (${item.buyer_email || 'N/A'})</p>
                <p>Ordered At: ${orderedDate}</p>
                <!-- No status directly on incoming order, handled by accept/decline -->
                ${item.trade_description ? `<p class="description">Desc: ${item.trade_description}</p>` : ''}
                ${item.trade_place ? `<p class="place"><i class='bx bx-map-pin'></i> ${item.trade_place}</p>` : ''}
                ${actionButtonsHTML} <!-- Add action buttons -->
            </div>
        `;
        container.appendChild(card);
    });
}

// --- Action Functions ---

async function removeCartItem(tradeId, token) {
    const errorDiv = document.getElementById('error'); // To show potential errors
    try {
        const response = await fetch(`http://127.0.0.1:5000/api/cart/${tradeId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `Failed to remove item (${response.status})`);
        }
        console.log(`Item ${tradeId} removed.`);
        // Optionally show a success message, but re-rendering the cart is usually enough

    } catch (error) {
        console.error('Error removing cart item:', error);
        if (errorDiv) errorDiv.textContent = `Error removing item: ${error.message}`;
        // Clear error message after a delay
        setTimeout(() => { if (errorDiv) errorDiv.textContent = ''; }, 4000);
    }
}

// --- New Listing Action Function ---
async function removeListing(tradeId, token) {
    const errorDiv = document.getElementById('error');
    try {
        const response = await fetch(`http://127.0.0.1:5000/api/trades/${tradeId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `Failed to remove listing (${response.status})`);
        }
        console.log(`Listing ${tradeId} removed.`);
        showNotification('Listing removed successfully.', 'success');
        // Refresh profile data to show updated listings and stats
        await fetchProfileData(token);

    } catch (error) {
        console.error('Error removing listing:', error);
        showNotification(`Error removing listing: ${error.message}`, 'error');
        // Optionally update errorDiv as well
        // if (errorDiv) errorDiv.textContent = `Error removing listing: ${error.message}`;
        // setTimeout(() => { if (errorDiv) errorDiv.textContent = ''; }, 4000);
    }
}

async function submitRating(tradeId, ratingValue, token) {
    const errorDiv = document.getElementById('error');
    console.log(`Submitting rating: ${ratingValue} for trade ID: ${tradeId}`); // Debug log
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
        console.log(`Rating submitted for ${tradeId}.`);
        // Refresh profile data to show updated rating and stats
        await fetchProfileData(token);

    } catch (error) {
        console.error('Error submitting rating:', error);
        if (errorDiv) errorDiv.textContent = `Error submitting rating: ${error.message}`;
        setTimeout(() => { if (errorDiv) errorDiv.textContent = ''; }, 4000);
    }
}

// --- Function to handle ordering an item --- 
async function orderItem(tradeId, token) {
    if (!tradeId || !token) {
        showNotification('Missing information to place order.', 'error');
        return;
    }

    try {
        const response = await fetch(`http://127.0.0.1:5000/api/cart/items/${tradeId}/order`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json' // Although body is empty, header is good practice
            },
            // No body needed for this specific endpoint
        });

        const result = await response.json();

        if (response.ok) {
            showNotification(`Order placed successfully for item ${tradeId}! Status set to 'ordered'.`, 'success');
            // Refresh cart data to show updated status
            await fetchCartData(token);
            // Also potentially refresh incoming orders if the user is also a seller (edge case, but possible)
            // Consider if a full profile refresh is better here
            await fetchIncomingOrders(token);
        } else {
            throw new Error(result.message || `Failed to place order (${response.status})`);
        }
    } catch (error) {
        console.error('Error placing order:', error);
        showNotification(`Error placing order: ${error.message}`, 'error');
    }
}

// --- Seller Order Management Functions ---
async function acceptIncomingOrder(cartItemId, token) {
    try {
        // Call the NEW backend endpoint
        const response = await fetch(`http://127.0.0.1:5000/api/seller/orders/accept`, {
            method: 'POST', // Use POST
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json' // Add Content-Type
             },
             body: JSON.stringify({ cart_item_id: cartItemId }) // Send ID in body
        });
        const responseData = await response.json();
        if (!response.ok) {
            throw new Error(responseData.message || `Failed to accept order (${response.status})`);
        }
        showNotification(responseData.message || 'Order accepted successfully.', 'success');
        // Refresh all profile data as this changes listings, stats, and incoming orders
        await fetchProfileData(token);
    } catch (error) {
        console.error('Error accepting order:', error);
        showNotification(`Error accepting order: ${error.message}`, 'error');
    }
}

async function declineIncomingOrder(cartItemId, token) {
    try {
        // Call the NEW backend endpoint
        const response = await fetch(`http://127.0.0.1:5000/api/seller/orders/decline`, {
            method: 'POST', // Use POST
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json' // Add Content-Type
            },
            body: JSON.stringify({ cart_item_id: cartItemId }) // Send ID in body
        });
        const responseData = await response.json();
        if (!response.ok) {
            throw new Error(responseData.message || `Failed to decline order (${response.status})`);
        }
        showNotification(responseData.message || 'Order declined successfully.', 'success');
        // Refresh all profile data as this changes listings, stats, and incoming orders
        await fetchProfileData(token);
    } catch (error) {
        console.error('Error declining order:', error);
        showNotification(`Error declining order: ${error.message}`, 'error');
    }
}

// Remove old functions if they are no longer used
// function setupGuestUI() { ... }
// async function fetchProfile(token) { ... } // Replaced by fetchProfileData
