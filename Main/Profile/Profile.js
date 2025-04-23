document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('authToken');

    // --- Element References ---
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error');
    const profileActionsDiv = document.getElementById('profile-actions');
    const logoutButton = document.getElementById('logout-button');
    // Header elements
    const profileHeaderSection = document.querySelector('.profile-header');
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

    // --- Edit Listing Modal Elements ---
    const editModal = document.getElementById('editListingModal');
    const editForm = document.getElementById('editListingForm');
    const closeButton = editModal.querySelector('.close-button');
    const cancelButton = editModal.querySelector('.cancel-button');
    const editTradeIdInput = document.getElementById('editTradeId');
    const editItemNameInput = document.getElementById('editItemName');
    const editItemPriceInput = document.getElementById('editItemPrice');
    const editItemQuantityInput = document.getElementById('editItemQuantity');
    const editItemDescriptionInput = document.getElementById('editItemDescription');
    const editItemPlaceInput = document.getElementById('editItemPlace');
    const editItemImageInput = document.getElementById('editItemImage');

    // --- Payment Modal Elements ---
    const paymentModal = document.getElementById('paymentModal');
    const paymentCloseButton = paymentModal?.querySelector('.payment-close-btn');
    const paymentCancelButton = paymentModal?.querySelector('.payment-cancel-btn');
    const paymentQRCodeContainer = document.getElementById('payment-qr-code-container');
    const paymentAmountSpan = document.getElementById('payment-amount');
    const confirmPaymentButton = document.getElementById('confirm-payment-btn');
    let currentCartItemIdForPayment = null; // To store the ID for the confirm action

    // --- Global variable to store profile data for easy access ---
    let userProfileData = null;

    // --- Initial State ---
    loadingDiv.style.display = 'block'; // Show loading initially
    errorDiv.textContent = '';
    // Hide content sections until data is loaded or guest view is confirmed
    if (profileHeaderSection) profileHeaderSection.style.display = 'none';
    if (cartSection) cartSection.style.display = 'none';
    if (listingsSection) listingsSection.style.display = 'none';
    if (incomingOrdersSection) incomingOrdersSection.style.display = 'none';
    if (statsSection) statsSection.style.display = 'none';
    if (profileActionsDiv) profileActionsDiv.style.display = 'none';
    const paymentSection = document.querySelector('.profile-payment-info');
    if (paymentSection) paymentSection.style.display = 'none';

    // --- Logic based on login state ---
    if (token) {
        console.log("Token found, fetching profile data...");
        document.body.classList.remove('guest-view-active'); // Ensure class is removed for logged-in users
        fetchProfileData(token);
        if (profileActionsDiv) profileActionsDiv.style.display = ''; // Reset display style

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
        document.body.classList.add('guest-view-active'); // Add class for guest view
        loadingDiv.style.display = 'none';
        // Show a message or redirect for guests
        if (profileFullname) profileFullname.textContent = 'Guest';
        if (profileEmail) profileEmail.textContent = 'Please log in to view your profile.';
        if (profileHeaderSection) profileHeaderSection.style.display = '';
        // Optionally hide stats/cart/listings for guests or show a prompt
        if (statsSection) statsSection.style.display = 'none';
        if (cartSection) cartSection.style.display = 'none';
        if (listingsSection) listingsSection.style.display = 'none';
        if (incomingOrdersSection) incomingOrdersSection.style.display = 'none';
        // Explicitly hide the logout button if it exists
        if (logoutButton) logoutButton.style.display = 'none';
        // ADDED: Explicitly hide payment info section for guests
        const paymentSection = document.querySelector('.profile-payment-info');
        if (paymentSection) paymentSection.style.display = 'none';
    }

    // --- Event Delegation for Cart Container ---
    if (cartContainer) {
        cartContainer.addEventListener('click', async (event) => {
            const currentToken = localStorage.getItem('authToken'); // Re-get token
            if (!currentToken) {
                showNotification('Please log in to manage your cart.', 'warning');
                return;
            }

            // Handle Remove Button
            if (event.target.closest('.remove-cart-item-btn')) {
                const button = event.target.closest('.remove-cart-item-btn');
                const cartItemId = button.dataset.cartItemId;
                if (cartItemId && confirm('Are you sure you want to remove this item from your cart?')) {
                    await removeCartItem(cartItemId, currentToken);
                    await fetchCartData(currentToken);
                }
            } 
            // Handle Order Button
            else if (event.target.closest('.order-btn')) {
                const button = event.target.closest('.order-btn');
                const cartItemId = button.dataset.cartItemId;
                if (cartItemId) {
                    await orderItem(cartItemId, currentToken);
                }
            }
            // --- Handle Pay Button Click --- 
            else if (event.target.closest('.pay-btn')) {
                const button = event.target.closest('.pay-btn');
                const cartItemId = button.dataset.cartItemId;
                const amount = button.dataset.amount;
                const tradeName = button.dataset.tradeName; // Get trade name
                if (cartItemId && amount && tradeName) { 
                    currentCartItemIdForPayment = cartItemId; // Store for confirmation
                    await showPaymentModal(cartItemId, amount, tradeName, currentToken);
                }
            }
            // Handle Rating Star clicks (moved from listings container)
            else if (event.target.classList.contains('rate-star')) {
                 const star = event.target;
                 const ratingControls = star.closest('.rate-trade-controls');
                 const cartItemId = ratingControls?.dataset.cartItemId;
                 const ratingValue = star.dataset.value;

                 if (cartItemId && ratingValue) {
                    console.log(`Rating ${ratingValue} clicked for cart item ${cartItemId}`);
                    await submitRating(cartItemId, parseInt(ratingValue, 10), currentToken);
                 } else {
                    console.error("Missing cartItemId or ratingValue for rating action.");
                 }
            }
        });
    }

    // Event Delegation for Listings Container
    if (listingsContainer) {
        listingsContainer.addEventListener('click', async (event) => {
            const token = localStorage.getItem('authToken'); 
            if (!token) return; 

            const removeButton = event.target.closest('.remove-listing-btn');
            const editButton = event.target.closest('.edit-listing-btn');

            // Handle Remove Listing clicks
            if (removeButton) {
                const tradeId = removeButton.dataset.tradeId;
                if (tradeId && confirm('Are you sure you want to permanently remove this listing?')) {
                    await removeListing(tradeId, token);
                }
            }
            // Handle Edit button clicks
            else if (editButton) {
                 const tradeId = parseInt(editButton.dataset.tradeId, 10);

                 if (userProfileData && userProfileData.listings) {
                    const tradeToEdit = userProfileData.listings.find(item => item.id === tradeId);

                    if (tradeToEdit) {
                         openEditModal(tradeToEdit);
                    } else {
                         console.error('Could not find listing data for ID:', tradeId);
                         showNotification('Could not load listing data to edit.', 'error');
                    }
                 } else {
                     console.error('Profile data or listings not loaded when trying to edit.'); // <-- Log 6: Data missing?
                     showNotification('Profile data not loaded yet. Cannot edit.', 'error');
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
            const completeButton = event.target.closest('.complete-order-btn'); // Added complete button
            const refuseButton = event.target.closest('.refuse-order-btn');

            if (acceptButton) {
                const cartItemId = acceptButton.dataset.cartItemId;
                console.log("Accept button clicked for cart item ID:", cartItemId); // Log 1: Button clicked
                if (cartItemId && confirm('Are you sure you want to accept this order?')) {
                    console.log("Calling acceptIncomingOrder..."); // Log 2: Calling function
                    await acceptIncomingOrder(cartItemId, token);
                }
            } else if (declineButton) {
                const cartItemId = declineButton.dataset.cartItemId;
                if (cartItemId && confirm('Are you sure you want to decline this order?')) {
                    await declineIncomingOrder(cartItemId, token);
                }
            } else if (completeButton) { // Handle Complete Payment
                const cartItemId = completeButton.dataset.cartItemId;
                if (cartItemId && confirm('Confirm you have received payment and want to complete this order?')) {
                    await completeIncomingOrder(cartItemId, token);
                }
            }else if (refuseButton) { // Handle Refuse Payment
                const cartItemId = refuseButton.dataset.cartItemId;
                if (cartItemId && confirm('Confirm you have not received payment and want to refuse this order?')) {
                    await refuseIncomingOrder(cartItemId, token);
                }
            }
        });
    }

    // --- Edit Listing Modal Functions ---
    function openEditModal(trade) {
        if (!trade) return;
        // Populate the form
        editTradeIdInput.value = trade.id;
        editItemNameInput.value = trade.name || '';
        editItemPriceInput.value = trade.price !== null ? trade.price.toString() : '';
        editItemQuantityInput.value = trade.quantity !== null ? trade.quantity.toString() : '';
        editItemDescriptionInput.value = trade.description || '';
        editItemPlaceInput.value = trade.place || '';
        editItemImageInput.value = trade.image || '';
        editModal.style.display = 'block';
    }

    function closeEditModal() {
        editModal.style.display = 'none';
        editForm.reset(); // Clear form fields
    }

    async function handleEditFormSubmit(event) {
        event.preventDefault(); // Prevent default form submission
        const tradeId = editTradeIdInput.value;
        const token = localStorage.getItem('authToken');

        const updatedData = {
            name: editItemNameInput.value,
            price: parseFloat(editItemPriceInput.value),
            quantity: parseInt(editItemQuantityInput.value, 10),
            description: editItemDescriptionInput.value,
            place: editItemPlaceInput.value,
            image: editItemImageInput.value,
        };

        // Basic validation before sending
        if (!updatedData.name || isNaN(updatedData.price) || updatedData.price < 0 || isNaN(updatedData.quantity) || updatedData.quantity < 0) {
            showNotification('Please fill in required fields (Name, Price, Quantity) correctly.', 'error');
            return;
        }

        console.log(`Updating trade ${tradeId} with data:`, updatedData);

        try {
            const response = await fetch(`${API_BASE_URL}/api/trades/${tradeId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(updatedData)
            });

            const result = await response.json();

            if (response.ok) {
                showNotification('Listing updated successfully!', 'success');
                closeEditModal();
                // Re-fetch profile data to show updated listing
                await fetchProfileData(token);
            } else {
                showNotification(`Error updating listing: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('Error updating listing:', error);
            showNotification('An error occurred while updating the listing.', 'error');
        }
    }

    // --- Event Listeners ---

    // Close modal listeners
    if (closeButton) {
        closeButton.onclick = closeEditModal;
    }
    if (cancelButton) {
        cancelButton.onclick = closeEditModal;
    }
    // Close modal if clicking outside of it
    window.onclick = function(event) {
        if (event.target == editModal) {
            closeEditModal();
        }
    }

    // Form submission listener
    if (editForm) {
        editForm.addEventListener('submit', handleEditFormSubmit);
    }

    // --- Main Fetch and Render Logic ---
    async function fetchProfileData(token) {
        loadingDiv.style.display = 'block';
        errorDiv.textContent = '';

        try {
            // Fetch full profile data from the new endpoint
            const response = await fetch(`${API_BASE_URL}/api/profile`, { // Changed endpoint
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json'
                }
            });


            if (!response.ok) {
                const errorText = await response.text(); // Get raw error text
                console.error("Profile fetch error response text:", errorText); // Log: Error response text
                throw new Error(`Failed to fetch profile data: ${response.status} - ${errorText}`);
            }

            const data = await response.json();

            // Check if data contains the expected user_profile object
            if (!data || !data.user_profile) {
                throw new Error('Invalid profile data structure received from server.');
            }

            userProfileData = data.user_profile; // Store the user profile data

            // --- Update Basic Profile Header ---
            if (profileFullname) profileFullname.textContent = userProfileData.fullname || 'N/A';
            if (profileEmail) profileEmail.textContent = userProfileData.email || 'N/A';
            if (profileHeaderSection) profileHeaderSection.style.display = '';

            // --- Update Payment Information Display ---
            const bankNameDisplay = document.getElementById('display-bank-name');
            const bankAccNameDisplay = document.getElementById('display-bank-account-name');
            const bankAccNumDisplay = document.getElementById('display-bank-account-number');

            if (bankNameDisplay) bankNameDisplay.textContent = userProfileData.bank_name || 'Not set';
            if (bankAccNameDisplay) bankAccNameDisplay.textContent = userProfileData.bank_account_name || 'Not set';
            if (bankAccNumDisplay) bankAccNumDisplay.textContent = userProfileData.bank_account_number || 'Not set';

            // --- Fetch other related data (listings, cart, orders, stats) ---
            // Note: Stats are now calculated client-side or need a separate endpoint if required
            await fetchListingsData(token); // Fetch user's listings
            await fetchCartData(token); // Fetch cart data
            await fetchIncomingOrders(token); // Fetch incoming orders
            calculateAndDisplayStats(); // Calculate stats based on fetched listings/orders

            // --- Show relevant sections by resetting inline display style --- 
            if (cartSection) cartSection.style.display = '';
            if (listingsSection) listingsSection.style.display = '';
            if (incomingOrdersSection) incomingOrdersSection.style.display = '';
            if (statsSection) statsSection.style.display = '';
            const paymentSection = document.querySelector('.profile-payment-info');
            if (paymentSection) paymentSection.style.display = '';


        } catch (error) {
            console.error('Error fetching or processing profile data:', error); // Log 5: Catch block error
            document.body.classList.add('guest-view-active'); // Add class for guest view
            errorDiv.textContent = ``;
            
            // Hide sections on error
            if (profileFullname) profileFullname.textContent = 'Guest';
            if (profileEmail) profileEmail.textContent = 'Please log in to view your profile.';
            if (profileHeaderSection) profileHeaderSection.style.display = '';
            if (cartSection) cartSection.style.display = 'none';
            if (listingsSection) listingsSection.style.display = 'none';
            if (incomingOrdersSection) incomingOrdersSection.style.display = 'none';
            if (statsSection) statsSection.style.display = 'none';
            if (logoutButton) logoutButton.style.display = 'none';
            const paymentSection = document.querySelector('.profile-payment-info');
            if (paymentSection) paymentSection.style.display = 'none';
        } finally {
            loadingDiv.style.display = 'none';
        }
    }

    // Helper function to calculate and display stats (if needed)
    function calculateAndDisplayStats() {
        if (!userProfileData) return; // Needs profile data (especially counts if added)
        // Fetch listings/orders first if stats depend on them
        // Example: Calculate listings count
        const listingsCount = userProfileData.listings ? userProfileData.listings.length : 0;
        if (listingsCountEl) listingsCountEl.textContent = listingsCount;
        
        // Example: Success percentage (requires completed/cancelled counts)
        // These counts should ideally come directly from the /api/profile endpoint
        const successRate = userProfileData.successful_trades_percentage; // Use the value from backend
        if (successfulTradesEl) successfulTradesEl.textContent = `${successRate}%`;

        // Example: Seller Average Rating (needs listings with ratings)
        // This calculation might be complex client-side, better from backend if possible
        const avgRating = userProfileData.seller_average_rating; // Use the value from backend
        if (averageRatingEl) {
            averageRatingEl.innerHTML = avgRating != 0 ? generateStars(avgRating) : 'Not Rated Yet';
        }
    }

    // --- Fetch User Listings --- (Separate function)
    async function fetchListingsData(token) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/profile/stats`, { // Keep using stats endpoint for listings
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json'
                }
            });
            if (!response.ok) throw new Error('Failed to fetch listings');
            const data = await response.json();
            userProfileData.listings = data.listings || []; // Store listings under profile data
            userProfileData.seller_average_rating = data.seller_average_rating || 0;
            userProfileData.successful_trades_percentage = data.successful_trades_percentage || 0;
            renderListings(userProfileData.listings);
        } catch (error) {
            console.error('Error fetching listings:', error);
            if (listingsContainer) listingsContainer.innerHTML = '<p class="error-message">Could not load your listings.</p>';
        }
    }

    // --- Edit Payment Info Form Handling ---
    const paymentDisplayDiv = document.getElementById('payment-info-display');
    const paymentForm = document.getElementById('edit-payment-info-form');
    const editPaymentBtn = document.getElementById('edit-payment-info-btn');
    const cancelPaymentBtn = document.getElementById('cancel-edit-payment-btn');

    const editBankNameInput = document.getElementById('edit-bank-name');
    const editAccNameInput = document.getElementById('edit-bank-account-name');
    const editAccNumInput = document.getElementById('edit-bank-account-number');

    if (editPaymentBtn && paymentForm && paymentDisplayDiv) {
        editPaymentBtn.addEventListener('click', () => {
            // Populate form with current values before showing
            if (userProfileData) {
                editBankNameInput.value = userProfileData.bank_name || '';
                editAccNameInput.value = userProfileData.bank_account_name || '';
                editAccNumInput.value = userProfileData.bank_account_number || '';
            }
            paymentForm.classList.remove('hidden-form');
        });
    }

    if (cancelPaymentBtn && paymentForm && paymentDisplayDiv) {
        cancelPaymentBtn.addEventListener('click', () => {
            paymentForm.classList.add('hidden-form');
            paymentForm.reset(); // Clear any changes
        });
    }

    if (paymentForm) {
        paymentForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const token = localStorage.getItem('authToken');
            if (!token) {
                showNotification('Authentication error. Please log in again.', 'error');
                return;
            }

            const updatedData = {
                bank_name: editBankNameInput.value.trim(),
                bank_account_name: editAccNameInput.value.trim(),
                bank_account_number: editAccNumInput.value.trim(),
            };

            // Optional: Add more validation here if needed

            try {
                const response = await fetch(`${API_BASE_URL}/api/profile/payment`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(updatedData)
                });

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.message || 'Failed to update payment info');
                }

                showNotification('Payment information updated successfully!', 'success');
                
                // Update local user data and display
                if (result.payment_info) {
                    userProfileData.bank_name = result.payment_info.bank_name;
                    userProfileData.bank_account_name = result.payment_info.bank_account_name;
                    userProfileData.bank_account_number = result.payment_info.bank_account_number;
                    
                    // Update display elements
                    document.getElementById('display-bank-name').textContent = userProfileData.bank_name || 'Not set';
                    document.getElementById('display-bank-account-name').textContent = userProfileData.bank_account_name || 'Not set';
                    document.getElementById('display-bank-account-number').textContent = userProfileData.bank_account_number || 'Not set';
                }

                // Hide form, show display
                paymentForm.classList.add('hidden-form');
                paymentDisplayDiv.classList.remove('hidden-form');

            } catch (error) {
                console.error('Error updating payment info:', error);
                showNotification(`Error: ${error.message}`, 'error');
            }
        });
    }


    async function fetchCartData(token) {
        try {
            const cartResponse = await fetch(`${API_BASE_URL}/api/cart`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!cartResponse.ok) {
                const errorData = await cartResponse.json();
                throw new Error(errorData.message || `Failed to fetch cart (${cartResponse.status})`);
            }
            const cartData = await cartResponse.json();

            // Populate Cart
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
        try {
            const response = await fetch(`${API_BASE_URL}/api/profile/incoming_orders`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `Failed to fetch incoming orders (${response.status})`);
            }
            const data = await response.json();

            // Populate Incoming Orders
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
            card.className = 'listing-card';
            const formattedPrice = typeof item.price === 'number' ? item.price.toFixed(0) + ' VND' : item.price;
            const listedDate = new Date(item.created_at).toLocaleString();
            const productRatingHTML = item.average_product_rating !== null ? generateStars(item.average_product_rating) : '<span class="no-rating">Not Rated</span>';

            card.innerHTML = `
                <div class="listing-image">
                    ${item.image ? `<img src="${item.image}" alt="${item.name}">` : ''}
                    <h3 class="listing-title">${item.name}</h3>
                </div>
                <div class="listing-content">
                    <div class="listing-details">
                        <div class="detail-row">
                            <span class="detail-label"><i class='bx bx-money'></i> Unit Price</span>
                            <span class="detail-value">${formattedPrice}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label"><i class='bx bx-package'></i> Quantity</span>
                            <span class="detail-value">${item.quantity}</span>
                        </div>
                        ${item.place ? `
                        <div class="detail-row">
                            <span class="detail-label"><i class='bx bx-map-pin'></i> Address</span>
                            <span class="detail-value">${item.place}</span>
                        </div>
                        ${item.description ? `
                        <div class="detail-row">
                            <span class="detail-label"><i class='bx bx-text'></i> Description</span>
                            <span class="detail-value">${item.description}</span>
                        </div>
                        ` : ''}
                        <div class="detail-row">
                            <span class="detail-label"><i class='bx bx-star'></i> Avg. Rating</span>
                            <span class="detail-value">${productRatingHTML}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label"><i class='bx bx-calendar'></i> Listed At</span>
                            <span class="detail-value">${listedDate}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label"><i class='bx bx-check-circle'></i> Status</span>
                            <span class="detail-value status-${item.status === 'Available' ? 'available' : 'unavailable'}">${item.status || 'N/A'}</span>
                        </div>
                        ` : ''}
                    </div>
                    <div class="listing-actions">
                        <button class="edit-listing-btn" data-trade-id="${item.id}">
                            <i class='bx bx-edit'></i> Edit
                        </button>
                        <button class="remove-listing-btn" data-trade-id="${item.id}">
                            <i class='bx bx-trash'></i> Remove
                        </button>
                    </div>
                </div>
            `;
            listingsContainer.appendChild(card);
        });
    }

    function renderCart(cartItems) {
        if (!cartContainer) return;
        cartContainer.innerHTML = ''; // Clear previous items

        if (cartItems && cartItems.length > 0) {
            cartItems.forEach(item => {
                const cartItemCard = document.createElement('div');
                cartItemCard.className = 'item-card';
                cartItemCard.dataset.tradeId = item.id; // Use trade ID for context
                cartItemCard.dataset.cartItemId = item.cart_item_id; // Store cart item ID if available

                const price = item.price.toFixed(0);
                const quantity = item.quantity || 0;
                const total = (price * quantity).toFixed(0) + ' VND';
                const status = item.cart_status || 'pending'; // Get status
                let statusText = status.charAt(0).toUpperCase() + status.slice(1);
                let actionButtonHTML = '';

                // --- Determine Action Button based on Status ---
                if (status === 'pending') {
                    statusText = 'In Cart';
                    actionButtonHTML = `
                        <button class="item-btn order-btn" data-cart-item-id="${item.cart_item_id}" title="Confirm purchase with seller">
                            <i class='bx bx-send'></i> Order Now
                        </button>
                        <button class="item-btn remove-cart-item-btn" data-cart-item-id="${item.cart_item_id}" title="Remove from cart">
                            <i class='bx bx-trash'></i> Remove
                        </button>
                    `;
                } else if (status === 'ordered') {
                    statusText = 'Order Placed (Awaiting Seller)';
                     actionButtonHTML = `
                         <button class="item-btn remove-cart-item-btn" data-cart-item-id="${item.cart_item_id}" title="Cancel Order (if possible - depends on seller action)">
                             <i class='bx bx-x-circle'></i> Cancel
                         </button>
                     `; // Maybe add cancel button later
                } else if (status === 'accepted') { // NEW: Seller accepted, awaiting payment
                     statusText = 'Accepted (Awaiting Payment)';
                     actionButtonHTML = `
                         <button class="item-btn pay-btn" data-trade-id="${item.id}" data-cart-item-id="${item.cart_item_id}" data-amount="${total}" data-trade-name="${item.name}">
                             <i class='bx bx-qr'></i> Pay Now
                         </button>
                         <button class="item-btn remove-cart-item-btn" data-cart-item-id="${item.cart_item_id}" title="Cancel Order">
                             <i class='bx bx-trash'></i> Cancel
                         </button>
                    `;
                } else if (status === 'payment_confirmed') { // NEW: Buyer paid, awaiting seller completion
                    statusText = 'Payment Confirmed (Awaiting Completion)';
                    actionButtonHTML = '<span class="status-text">Awaiting seller confirmation.</span>'; // No actions for buyer
                } else if (status === 'completed') {
                    statusText = 'Order Completed';
                    // --- Rating Display Logic ---
                    if (item.current_user_rating_score !== null && item.current_user_rating_score !== undefined) {
                        // User has already rated
                        actionButtonHTML = `<div class="already-rated">You rated: ${generateStars(item.current_user_rating_score)}</div>
                                        <button class="item-btn remove-cart-item-btn" data-cart-item-id="${item.cart_item_id}" title="Remove completed order from view">
                                            <i class='bx bx-trash'></i> Remove
                                        </button>
                        `;
                    } else {
                        // User has not rated yet, show input stars
                        actionButtonHTML = `
                            <div class="rate-trade-controls" data-cart-item-id="${item.cart_item_id}">
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
                    }
                    // --- End Rating Display Logic ---
                } else if (status === 'cancelled') {
                     statusText = 'Order Cancelled';
                     actionButtonHTML = `
                        <button class="item-btn remove-cart-item-btn" data-cart-item-id="${item.cart_item_id}" title="Remove cancelled order from view">
                            <i class='bx bx-trash'></i> Remove
                        </button>
                    `; // Changed title slightly for cancelled items
                }
                // --- End Status Check ---


                cartItemCard.innerHTML = `
                    <div class="item-image">
                        ${item.image ? `<img src="${item.image}" alt="${item.name}">` : ''}
                        <h3 class="item-title">${item.name}</h3>
                    </div>
                    <div class="item-content">
                        <div class="item-details">
                            <div class="item-detail-row">
                                <span class="item-detail-label"><i class='bx bx-user'></i> Seller</span>
                                <span class="item-detail-value">${item.business_name || 'N/A'} ${item.seller_email ? `(${item.seller_email})` : ''}</span>
                            </div>
                            <div class="item-detail-row">
                                <span class="item-detail-label"><i class='bx bx-money'></i> Unit Price</span>
                                <span class="item-detail-value">${price} VND</span>
                            </div>
                            <div class="item-detail-row">
                                <span class="item-detail-label"><i class='bx bx-package'></i> Quantity</span>
                                <span class="item-detail-value">${quantity}</span>
                            </div>
                            <div class="item-detail-row">
                                <span class="item-detail-label"><i class='bx bx-money'></i> Total Price</span>
                                <span class="item-detail-value">${total}</span>
                            </div>
                            <div class="item-detail-row">
                                <span class="item-detail-label"><i class='bx bx-map-pin'></i> Address</span>
                                <span class="item-detail-value">${item.trade_place}</span>
                            </div>
                            <div class="item-detail-row">
                                <span class="item-detail-label"><i class='bx bx-text'></i> Description</span>
                                <span class="item-detail-value">${item.trade_description}</span>
                            </div>
                            <div class="item-detail-row">
                                <span class="item-detail-label"><i class='bx bx-check-circle'></i> Status</span>
                                <span class="item-detail-value">${statusText}</span>
                            </div>
                        </div>
                        <div class="item-actions">
                            ${actionButtonHTML}
                        </div>
                    </div>
                `;
                cartContainer.appendChild(cartItemCard);
            });
        } else {
            cartContainer.innerHTML = '<p>Your cart is empty.</p>';
        }
    }

    // --- Updated Function to Render Incoming Orders ---
    function renderIncomingOrders(orders) {
        if (!incomingOrdersContainer) return;
        incomingOrdersContainer.innerHTML = ''; // Clear previous orders

        if (orders && orders.length > 0) {
            orders.forEach(order => {
                const orderCard = document.createElement('div');
                orderCard.className = 'incoming-order-card'; // Use a distinct class
                orderCard.dataset.cartItemId = order.cart_item_id; // Store cart item ID

                const price = order.trade_price || 0;
                const quantity = order.ordered_quantity || 0;
                const total = (price * quantity).toFixed(0) + ' VND';
                const status = order.status || 'ordered'; // Get status from order data if available
                let actionButtonHTML = '';

                // --- Determine Action Button based on Status ---
                if (status === 'ordered') {
                     actionButtonHTML = `
                        <button class="item-btn accept-order-btn" data-cart-item-id="${order.cart_item_id}">
                            <i class='bx bx-check-circle'></i> Accept Order
                        </button>
                        <button class="item-btn decline-order-btn" data-cart-item-id="${order.cart_item_id}">
                            <i class='bx bx-x-circle'></i> Decline Order
                        </button>
                    `;
                } else if (status === 'payment_confirmed') { // NEW: Buyer confirmed payment
                     actionButtonHTML = `
                        <button class="item-btn complete-order-btn" data-cart-item-id="${order.cart_item_id}">
                            <i class='bx bx-check-circle'></i> Confirm Payment
                        </button>
                        <button class="item-btn refuse-order-btn" data-cart-item-id="${order.cart_item_id}">
                            <i class='bx bx-x-circle'></i> Refuse Payment
                        </button>
                    `;
                } else {
                     // Handle other statuses like 'accepted' (awaiting payment) if needed
                     if (status === 'accepted') {
                         actionButtonHTML = `<span class="status-text status-accepted">Awaiting Buyer Payment...</span>`; // Updated text
                     } else {
                         actionButtonHTML = `<span class="status-text">Status: ${status}</span>`; // Fallback
                     }
                }
                // --- End Status Check ---

                orderCard.innerHTML = `
                    <div class="order-item-image">
                        ${order.trade_image ? `<img src="${order.trade_image}" alt="${order.trade_name}">` : ''}
                        <h3 class="order-item-title">${order.trade_name}</h3>
                    </div>
                    <div class="order-item-content">
                        <div class="order-item-details">
                            <div class="order-detail-row">
                                <span class="order-detail-label"><i class='bx bx-money'></i> Total Price</span>
                                <span class="order-detail-value">${total}</span>
                            </div>
                            <div class="order-detail-row">
                                <span class="order-detail-label"><i class='bx bx-package'></i> Quantity</span>
                                <span class="order-detail-value">${quantity}</span>
                            </div>
                            <div class="order-detail-row">
                                <span class="order-detail-label"><i class='bx bx-user'></i> Buyer</span>
                                <span class="order-detail-value">${order.buyer_fullname || 'N/A'} ${order.buyer_email ? `(${order.buyer_email})` : ''}</span>
                            </div>
                            <div class="order-detail-row">
                                <span class="order-detail-label"><i class='bx bx-calendar'></i> Ordered At</span>
                                <span class="order-detail-value">${new Date(order.ordered_at).toLocaleString()}</span>
                            </div>
                            <div class="order-detail-row">
                                <span class="order-detail-label"><i class='bx bx-check-circle'></i> Status</span>
                                <span class="order-detail-value">${status === 'accepted' ? 'Accepted (Awaiting Payment)' : (status.charAt(0).toUpperCase() + status.slice(1))}</span>
                            </div>
                        </div>
                        <div class="order-item-actions">
                            ${actionButtonHTML}
                        </div>
                    </div>
                `;
                incomingOrdersContainer.appendChild(orderCard);
            });
        } else {
            incomingOrdersContainer.innerHTML = '<p>You have no incoming orders.</p>';
        }
    }

    // --- Action Functions ---

    async function removeCartItem(cartItemId, token) {
        const errorDiv = document.getElementById('error'); // To show potential errors
        try {
            const response = await fetch(`${API_BASE_URL}/api/cart/items/${cartItemId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!response.ok) {
                const errorData = await response.json();
                if (response.status === 404) {
                    throw new Error(errorData.message || 'Cart item not found.');
                } else if (response.status === 403) {
                    throw new Error(errorData.message || 'Not authorized.');
                }
                throw new Error(errorData.message || `Failed to remove item (${response.status})`);
            }
            console.log(`Cart item ${cartItemId} removed.`);
            showNotification('Item removed from cart.', 'success');
        } catch (error) {
            console.error('Error removing cart item:', error);
            showNotification(`Error removing item: ${error.message}`, 'error');
        }
    }

    // --- New Listing Action Function ---
    async function removeListing(tradeId, token) {
        const errorDiv = document.getElementById('error');
        try {
            const response = await fetch(`${API_BASE_URL}/api/trades/${tradeId}`, {
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
        }
    }

    async function submitRating(cartItemId, ratingValue, token) {
        const errorDiv = document.getElementById('error');
        console.log(`Submitting rating: ${ratingValue} for cart item ID: ${cartItemId}`); // Debug log
        try {
            const response = await fetch(`${API_BASE_URL}/api/cart/items/${cartItemId}/rate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ rating_score: ratingValue })
            });

            if (!response.ok) {
                const errorData = await response.json();
                 // Handle specific errors
                 if (response.status === 400) { // e.g., Bad rating value, order not completed
                     throw new Error(errorData.message || 'Could not submit rating (invalid value or order status).');
                 } else if (response.status === 404) { // Order item not found
                     throw new Error(errorData.message || 'Order item not found.');
                 } else if (response.status === 403) { // Not the buyer
                     throw new Error(errorData.message || 'Not authorized to rate this order.');
                 }
                throw new Error(errorData.message || `Failed to submit rating (${response.status})`);
            }
            console.log(`Rating submitted for cart item ${cartItemId}.`);
            showNotification('Rating submitted successfully!', 'success'); // Add success notification
            // Refresh profile data to show updated rating and stats
            await fetchProfileData(token);

        } catch (error) {
            console.error('Error submitting rating:', error);
            showNotification(`Error submitting rating: ${error.message}`, 'error'); // Use showNotification
        }
    }

    // --- Function to handle ordering an item --- 
    async function orderItem(cartItemId, token) {
        if (!cartItemId || !token) {
            showNotification('Missing information to place order.', 'error');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/cart/items/${cartItemId}/order`, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json' // Although body is empty, header is good practice
                },
                // No body needed for this specific endpoint
            });

            const result = await response.json();

            if (response.ok) {
                showNotification(result.message || `Order placed successfully! Status set to 'ordered'.`, 'success');
                // Refresh cart data to show updated status
                await fetchCartData(token);
                // Also potentially refresh incoming orders if the user is also a seller (edge case, but possible)
                // Consider if a full profile refresh is better here
                await fetchIncomingOrders(token);
            } else {
                 // Handle specific errors like 400 (e.g., bad status, insufficient stock) or 404 (not found), 403 (auth)
                 if (response.status === 400) {
                     throw new Error(result.message || 'Could not place order (e.g., insufficient stock or invalid status).');
                 } else if (response.status === 404) {
                     throw new Error(result.message || 'Cart item not found.');
                 } else if (response.status === 403) {
                    throw new Error(result.message || 'Not authorized.');
                 }
                 throw new Error(result.message || `Failed to place order (${response.status})`);
            }
        } catch (error) {
            console.error('Error placing order:', error);
            showNotification(`Error placing order: ${error.message}`, 'error');
        }
    }

    // --- Seller Order Management Functions ---
    async function acceptIncomingOrder(cartItemId, token) {
        console.log(`Entering acceptIncomingOrder for cartItemId: ${cartItemId}`); // Log 3: Function entered
        try {
            const response = await fetch(`${API_BASE_URL}/api/seller/orders/accept`, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                 },
                 body: JSON.stringify({ cart_item_id: parseInt(cartItemId, 10) })
            });
            console.log("Accept API Response Status:", response.status); // Log 4: API status
            const responseData = await response.json();
            console.log("Accept API Response Data:", responseData); // Log 5: API data

            if (!response.ok) {
                console.error("Accept API call failed:", responseData.message); // Log 6: API error message
                throw new Error(responseData.message || `Failed to accept order (${response.status})`);
            }
            showNotification(responseData.message || 'Order accepted successfully.', 'success');
            // Refresh relevant data
            console.log("[Accept Success] Refreshing incoming orders...");
            await fetchIncomingOrders(token);
            // Log the data *after* fetching
            console.log("[Accept Success] User profile data after refresh (check incoming orders status):", userProfileData); 
            await fetchCartData(token); // Refresh buyer view too, status changed
            calculateAndDisplayStats(); // Stats might change
        } catch (error) {
            console.error('Error in acceptIncomingOrder function:', error); // Log 8: Catch block
            showNotification(`Error accepting order: ${error.message}`, 'error');
        }
    }

    async function declineIncomingOrder(cartItemId, token) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/seller/orders/decline`, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ cart_item_id: parseInt(cartItemId, 10) }) // Send ID in body, ensure integer
            });
            const responseData = await response.json();
            if (!response.ok) {
                throw new Error(responseData.message || `Failed to decline order (${response.status})`);
            }
            showNotification(responseData.message || 'Order declined successfully.', 'success');
            // Refresh relevant data
            await fetchIncomingOrders(token);
            await fetchCartData(token); // Refresh buyer view too, status changed
            calculateAndDisplayStats(); // Stats might change
        } catch (error) {
            console.error('Error declining order:', error);
            showNotification(`Error declining order: ${error.message}`, 'error');
        }
    }

    // --- Payment Modal Functions ---
    async function showPaymentModal(cartItemId, amount, tradeName, token) {
        if (!paymentModal || !paymentQRCodeContainer || !paymentAmountSpan) return;
        
        paymentAmountSpan.textContent = `${amount} VND`;
        paymentQRCodeContainer.innerHTML = '<p>Fetching seller payment info...</p>'; // Loading state
        paymentModal.style.display = 'block';

        try {
            const response = await fetch(`${API_BASE_URL}/api/cart/items/${cartItemId}/seller-payment-info`, {
                 headers: { 'Authorization': `Bearer ${token}` }
            });
            const sellerInfo = await response.json();

            if (!response.ok) {
                if (response.status === 403) {
                    throw new Error(sellerInfo.message || 'Not authorized to view payment info.');
                } else if (response.status === 404) {
                    throw new Error(sellerInfo.message || 'Order item or associated trade not found.');
                }
                throw new Error(sellerInfo.message || 'Could not fetch seller payment details.');
            }

            const { bank_id, account_number, account_name } = sellerInfo;

            // Construct payment description (URL encode necessary parts)
            const buyerName = userProfileData?.fullname || 'Customer'; // Use fetched profile name
            const descriptionRaw = `${buyerName} orders ${tradeName}`;
            const descriptionEncoded = encodeURIComponent(descriptionRaw);
            const accountNameEncoded = encodeURIComponent(account_name || '');

            // Construct VietQR URL
            const qrUrl = `https://img.vietqr.io/image/${bank_id}-${account_number}-compact2.png?amount=${amount}&addInfo=${descriptionEncoded}&accountName=${accountNameEncoded}`;

            console.log("Generated QR URL:", qrUrl); // For debugging

            // Display QR Code
            paymentQRCodeContainer.innerHTML = `<img src="${qrUrl}" alt="Payment QR Code">`;

        } catch (error) {
            console.error("Error fetching/generating payment QR:", error);
            paymentQRCodeContainer.innerHTML = `<p class="error-message">Error: ${error.message}</p>`;
            // Maybe disable the confirm button if QR fails
            if(confirmPaymentButton) confirmPaymentButton.disabled = true;
        }
    }

    function closePaymentModal() {
        if (paymentModal) {
            paymentModal.style.display = 'none';
            // Reset QR code area and enable button
            if(paymentQRCodeContainer) paymentQRCodeContainer.innerHTML = '<p>Loading QR Code...</p>';
            if(confirmPaymentButton) confirmPaymentButton.disabled = false;
            currentCartItemIdForPayment = null; // Clear stored ID
        }
    }

    // Attach listeners to payment modal close/cancel buttons
    if (paymentCloseButton) paymentCloseButton.addEventListener('click', closePaymentModal);
    if (paymentCancelButton) paymentCancelButton.addEventListener('click', closePaymentModal);

    // Attach listener to "I Have Paid" button
    if (confirmPaymentButton) {
        confirmPaymentButton.addEventListener('click', async () => {
            const token = localStorage.getItem('authToken');
            if (!currentCartItemIdForPayment || !token) {
                showNotification('Cannot confirm payment. Missing information.', 'error');
                return;
            }

            try {
                confirmPaymentButton.disabled = true; // Prevent double clicks

                // --- Add backend base URL --- 
                const response = await fetch(`${API_BASE_URL}/api/cart/items/${currentCartItemIdForPayment}/confirm-payment`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.message || 'Failed to confirm payment.');
                }
                
                // --- Show confirmation inside modal --- 
                if (paymentQRCodeContainer) {
                     paymentQRCodeContainer.innerHTML = '<h3 style="color: green;">Payment Confirmed!</h3>';
                }
                if (paymentCancelButton) paymentCancelButton.disabled = true; // Disable cancel too
                showNotification(result.message || 'Payment confirmed successfully!', 'success');
                
                // Close modal after a delay and refresh cart
                setTimeout(async () => {
                    closePaymentModal();
                    await fetchCartData(token); // Refresh cart view
                }, 2000); // Close after 2 seconds

            } catch (error) {
                 console.error("Error confirming payment:", error);
                 showNotification(`Error: ${error.message}`, 'error');
                 confirmPaymentButton.disabled = false; // Re-enable on error
            }
        });
    }

    // --- Add function for Seller Completing Order ---
    async function completeIncomingOrder(cartItemId, token) {
        try {
            // --- Add backend base URL --- 
            const response = await fetch(`${API_BASE_URL}/api/seller/orders/${cartItemId}/complete`, {
                 method: 'POST',
                 headers: { 'Authorization': `Bearer ${token}` }
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.message || 'Failed to complete order.');
            }
            showNotification(result.message || 'Order completed successfully!', 'success');
            // Refresh seller's incoming orders and potentially stats
            console.log("[Complete Success] Refreshing full profile data..."); // Updated log
            await fetchProfileData(token); // Refresh ALL profile data, which includes stats calc


        } catch (error) {
            console.error('Error completing order:', error);
            showNotification(`Error completing order: ${error.message}`, 'error');
        }
    }

    // --- Add function for Seller Refusing Order ---
    async function refuseIncomingOrder(cartItemId, token) {
        try {
            // --- Add backend base URL --- 
            const response = await fetch(`${API_BASE_URL}/api/seller/orders/${cartItemId}/refuse_payment`, {
                 method: 'POST',
                 headers: { 'Authorization': `Bearer ${token}` }
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.message || 'Failed to refuse order.');
            }
            showNotification(result.message || 'Order refused successfully!', 'success');
            // Refresh seller's incoming orders and potentially stats
            console.log("[Refuse Success] Refreshing full profile data..."); // Updated log
            await fetchProfileData(token); // Refresh ALL profile data, which includes stats calc


        } catch (error) {
            console.error('Error refusing order:', error);
            showNotification(`Error refusing order: ${error.message}`, 'error');
        }
    }

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

    // Function to show notifications (Ensure #notification-area exists in Profile.html)
    const showNotification = (message, type = 'success', duration = 5000) => {
        const notificationArea = document.getElementById('notification-area'); 
        if (!notificationArea) {
            console.error("Notification area element (#notification-area) not found!");
            return; // Stop if area doesn't exist
        }

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;

        const messageElement = document.createElement('span');
        messageElement.innerHTML = message; 

        const closeButton = document.createElement('button');
        closeButton.innerHTML = '&times;'; 
        closeButton.className = 'notification-close-btn';

        const closeNotification = () => {
            notification.style.opacity = '0';
            // Use transitionend event for smoother removal
            notification.addEventListener('transitionend', () => notification.remove(), { once: true });
            // Fallback timeout
            setTimeout(() => notification.remove(), 1000); 
        };

        closeButton.addEventListener('click', closeNotification);

        notification.appendChild(messageElement);
        notification.appendChild(closeButton);
        notificationArea.appendChild(notification);

        const autoCloseTimeout = setTimeout(closeNotification, duration);
        closeButton.addEventListener('click', () => clearTimeout(autoCloseTimeout));
    };

    // Add menu button functionality
    const menuBtn = document.querySelector('.menu-btn');
    const navbar = document.querySelector('.navbar');
    
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

}); // End of DOMContentLoaded event listener
