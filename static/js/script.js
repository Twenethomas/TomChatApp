// Establish Socket.IO connection
const socket = io.connect("http://127.0.0.1:5000");

// On page load, load default tab, friends and friend requests
document.addEventListener("DOMContentLoaded", () => {
    openTab("chats");
    loadFriends();
    loadFriendRequests();
});

// ----- Sidebar & Tab Functions -----
function openTab(tabName) {
    document.querySelectorAll(".tab-content").forEach(tab => tab.classList.remove("active"));
    document.getElementById(tabName).classList.add("active");
    document.querySelectorAll(".tab-button").forEach(button => button.classList.remove("active"));
    document.querySelector(`.tab-button[onclick="openTab('${tabName}')"]`).classList.add("active");
}
function openModal(modalId) {
    document.getElementById(modalId).classList.add("active");
}
function closeModal(modalId) {
    document.getElementById(modalId).classList.remove("active");
}
function closeAddFriendModal() {
    closeModal("add-friend-modal");
}

// ----- Load Friends (for Chat List) -----
function loadFriends() {
    fetch("/api/friends")
        .then(response => response.json())
        .then(friends => {
            // Sort friends: unread messages first, then online status
            friends.sort((a, b) => {
                if (b.unread_count !== a.unread_count) {
                    return b.unread_count - a.unread_count; // Higher unread first
                }
                return b.is_online - a.is_online; // Online users first
            });

            const chatList = document.getElementById("chat-list");
            chatList.innerHTML = "";
            
            friends.forEach(friend => {
                const listItem = document.createElement("li");
                listItem.setAttribute('data-unread', friend.unread_count);
                // In loadFriends() function
                listItem.innerHTML = `
                <div class="chat-avatar" style="position: relative">
                    <img src="${friend.profile_picture || '/static/images/default_profile.jpg'}" alt="${friend.username}">
                    ${friend.is_online ? '<div class="online-dot"></div>' : ''}
                </div>
                <div class="chat-details">
                    <div class="chat-header">
                        <div class="chat-name">${friend.username}</div>
                        <div class="chat-time">${friend.last_message?.time || ''}</div>
                    </div>
                    <div class="chat-preview">${friend.last_message?.text || ''}</div>
                </div>
                ${friend.unread_count > 0 ? `<span class="unread-badge">${friend.unread_count}</span>` : ''}
                `;
                
                // Click handler remains the same
                listItem.onclick = () => { 
                    selectChat(friend.custom_id, friend.username, friend.is_online);
                    // Reset unread count when chat is opened
                    const badge = listItem.querySelector('.unread-badge');
                    if (badge) badge.remove();
                    // Mark messages as read on backend
                    fetch(`/api/mark_as_read/${friend.custom_id}`, { method: 'POST' });
                };
                
                chatList.appendChild(listItem);
            });
        });
}
// ----- Select Chat & Load Messages -----
function selectChat(friendId, friendName,friend_status) {
     ;if( !friend_status){
       user_status = 'offline'
     } else {
        user_status = 'online'} 
    document.getElementById("chat-header-name").innerText = friendName;
    document.getElementById("chat-header-name").setAttribute("data-receiver-id", friendId);
    document.getElementById("chat-header-status").innerText = user_status;
    document.getElementById("message-input").disabled = false;
    document.getElementById("send-button").disabled = false;
    fetch(`/api/messages/${friendId}`)
        .then(response => response.json())
        .then(messages => {
            const chatMessages = document.getElementById("chat-messages");
            chatMessages.innerHTML = "";
            messages.forEach(msg => {
                const isCurrentUser = msg.sender_id === currentUser.custom_id;
                appendMessage(friendName, msg.message_text, msg.timestamp, isCurrentUser);
            });
        })
        .catch(error => console.error("Error loading messages:", error));
}

function appendMessage(sender, text, timestamp, isCurrentUser) {
    const chatMessages = document.getElementById("chat-messages");
    const messageElement = document.createElement("div");
    messageElement.classList.add("message", isCurrentUser ? "sent" : "received");
    messageElement.innerHTML = `
        <div class="message-content">
            <strong>${isCurrentUser ? "Me" : sender}</strong>: ${text}
            <div class="message-timestamp">${timestamp}</div>
        </div>
    `;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ----- Send Message -----
document.getElementById("send-button").addEventListener("click", () => {
    const receiverId = document.getElementById("chat-header-name").getAttribute("data-receiver-id");
    const messageInput = document.getElementById("message-input");
    const messageText = messageInput.value.trim();
    if (!receiverId || messageText === "") {
        alert("Select a user and enter a message.");
        return;
    }
    fetch("/api/send_message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ receiver_id: receiverId, message: messageText }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                appendMessage("Me", messageText, new Date().toLocaleTimeString(), true);
                messageInput.value = "";
            } else {
                alert(`Error: ${data.error}`);
            }
        })
        .catch(error => console.error("Error sending message:", error));
});

// ----- Real-Time Message Listener -----
// socket.on("receive_message", data => {
//     if (data.receiver_id === currentUser.custom_id) {
//         // Get current chat header name dynamically on each message receive
//         const chatHeaderElement = document.getElementById('chat-header-name');
//         const currentChatName = chatHeaderElement ? chatHeaderElement.innerText.trim() : '';
        
//         // Only append if the sender matches the currently open chat
//         if (data.sender_name.trim() === currentChatName) {
//             const isCurrentUser = data.sender_id === currentUser.custom_id;
//             appendMessage(data.sender_name, data.message_text, data.timestamp, isCurrentUser);
//         }
//     }
// });

socket.on("receive_message", data => {
    const currentChatId = document.getElementById("chat-header-name")?.dataset.receiverId;
    const isCurrentChat = data.sender_id === currentChatId;
    
    // Always append message if it's for the current chat
    if (data.receiver_id === currentUser.custom_id && isCurrentChat) {
        const isCurrentUser = data.sender_id === currentUser.custom_id;
        appendMessage(data.sender_name, data.message_text, data.timestamp, isCurrentUser);
    }

    // Handle unread counts and sorting for non-active chats
    if (data.receiver_id === currentUser.custom_id && !isCurrentChat) {
        const friendItem = [...document.querySelectorAll('#chat-list li')].find(li => {
            return li.querySelector('.chat-name').textContent === data.sender_name;
        });

        if (friendItem) {
            const badge = friendItem.querySelector('.unread-badge');
            const currentUnread = parseInt(friendItem.getAttribute('data-unread')) || 0;
            
            friendItem.setAttribute('data-unread', currentUnread + 1);
            
            if (badge) {
                badge.textContent = currentUnread + 1;
            } else {
                const newBadge = document.createElement('span');
                newBadge.className = 'unread-badge';
                newBadge.textContent = '1';
                friendItem.appendChild(newBadge);
            }
            
            sortChatList();
        }
    }
});
// ----- Friend Requests -----
function loadFriendRequests() {
    fetch("/api/friend_requests")
        .then(response => response.json())
        .then(data => {
            const friendRequestList = document.getElementById("friend-request-list");
            friendRequestList.innerHTML = "";
            data.forEach(request => {
                const listItem = document.createElement("li");
                listItem.innerHTML = `
                    <span>${request.sender_username}</span>
                    <button onclick="acceptFriendRequest('${request.request_id}')">Accept</button>
                    <button onclick="declineFriendRequest('${request.request_id}')">Decline</button>
                `;
                friendRequestList.appendChild(listItem);
            });
        })
        .catch(error => console.error("Error fetching friend requests:", error));
}

function acceptFriendRequest(requestId) {
    fetch(`/api/friend_request/accept/${requestId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Friend request accepted!");
                loadFriendRequests();
                loadFriends();
            } else {
                alert("Error: " + data.error);
            }
        });
}

function declineFriendRequest(requestId) {
    fetch(`/api/friend_request/decline/${requestId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Friend request declined!");
                loadFriendRequests();
            } else {
                alert("Error: " + data.error);
            }
        });
}

// Listen for real-time friend request events
socket.on("friend_request_received", () => { loadFriendRequests(); });
socket.on("friend_request_accepted", data => {
    alert(`Friend request accepted by ${data.receiver_id}`);
    loadFriendRequests();
    loadFriends();
});
socket.on("friend_request_declined", data => {
    alert(`Friend request declined by ${data.receiver_id}`);
    loadFriendRequests();
});

// ----- Search Users -----
// For Add Chat Modal
// function searchUsersForChat() {
//     const searchQuery = document.getElementById("search-user").value;
//     fetch(`/api/search_users?query=${searchQuery}`)
//         .then(response => response.json())
//         .then(data => {
//             const userList = document.getElementById("user-list");
//             userList.innerHTML = "";
//             data.forEach(user => {
//                 const listItem = document.createElement("li");
//                 listItem.innerHTML = `
//                     <div class="user-avatar">
//                         <img src="${user.profile_picture || '/static/images/default_profile.jpg'}" alt="${user.username}">
//                     </div>
//                     <div class="user-details">
//                         <span>${user.username}</span>
//                         <button onclick="sendFriendRequest('${user.custom_id}')">Add Friend</button>
//                     </div>
//                 `;
//                 userList.appendChild(listItem);
//             });
//         })
//         .catch(error => console.error("Error searching users for chat:", error));
// }

// document.addEventListener("DOMContentLoaded", () => {
//     openTab("chats");
//     loadFriends();
//     loadFriendRequests();
// });

// // ✅ FIX CHAT MESSAGE ALIGNMENT
// function appendMessage(sender, text, timestamp, isCurrentUser) {
//     const chatMessages = document.getElementById("chat-messages");
//     const messageElement = document.createElement("div");

//     if (sender === currentUser.custom_id) {
//         messageElement.classList.add("message", "sent");
//     } else {
//         messageElement.classList.add("message", "received");
//     }

//     messageElement.innerHTML = `
//         <div class="message-content">
//             <strong>${sender === currentUser.custom_id ? 'Me' : sender}</strong>: ${text}
//             <div class="message-timestamp">${timestamp}</div>
//         </div>
//     `;

//     chatMessages.appendChild(messageElement);
//     chatMessages.scrollTop = chatMessages.scrollHeight;
// }

// ✅ FIX SEARCH USERS FOR ADD FRIEND MODAL
function searchUsersForFriend() {
    const searchQuery = document.getElementById("search-friend").value;
    fetch(`/api/search_users?query=${searchQuery}`)
        .then(response => response.json())
        .then(data => {
            const friendList = document.getElementById("friend-list");
            friendList.innerHTML = "";
            data.forEach(user => {
                const listItem = document.createElement("li");
                listItem.innerHTML = `
                    <div class="user-avatar" >
                        <img src="${user.profile_picture || '/static/images/default_profile.jpg'}" alt="${user.username}">
                    </div>
                    <div class="user-details">
                        <span>${user.username}</span>
                    </div>
                    <button class="btn bg-success" onclick="sendFriendRequest('${user.custom_id}')" id="${user.custom_id}">Add Friend</button>

                `;
                friendList.appendChild(listItem);
            });
        })
        .catch(error => console.error("Error searching users for friend:", error));
}

// Send a friend request
function sendFriendRequest(receiverId) {
    fetch('/api/friend_request', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ receiver_id: receiverId }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Friend request sent!');
            document.getElementById(receiverId).remove()
            // closeAddFriendModal(); // Close the modal after sending the request
        } else {
            alert('Error: ' + data.error);
        }
    });
}

function sortChatList() {
    const chatList = document.getElementById("chat-list");
    const items = Array.from(chatList.children);
    
    items.sort((a, b) => {
        const aUnread = parseInt(a.getAttribute('data-unread')) || 0;
        const bUnread = parseInt(b.getAttribute('data-unread')) || 0;
        const aOnline = a.querySelector('.online-dot') ? 1 : 0;
        const bOnline = b.querySelector('.online-dot') ? 1 : 0;
        
        // Safely get timestamp elements
        const aTimeElement = a.querySelector('.chat-preview');
        const bTimeElement = b.querySelector('.chat-preview');
        const aTimestamp = aTimeElement ? aTimeElement.textContent : '';
        const bTimestamp = bTimeElement ? bTimeElement.textContent : '';

        if (bUnread !== aUnread) return bUnread - aUnread;
        if (bOnline !== aOnline) return bOnline - aOnline;
        return bTimestamp.localeCompare(aTimestamp);
    });

    // Re-append sorted items
    items.forEach(item => chatList.appendChild(item));
}