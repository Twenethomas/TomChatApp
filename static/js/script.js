// Establish Socket.IO connection
const socket = io.connect("https://192.168.1.10:5000");

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

// ----- Helper Functions -----

// Update unread badge in both chat list and online friends container
function updateUnreadBadge(friendId, newCount) {
    // Update in chat list
    const chatItem = document.querySelector(`#chat-list li[data-friend-id="${friendId}"]`);
    if (chatItem) {
        chatItem.setAttribute("data-unread", newCount);
        let badge = chatItem.querySelector(".unread-badge");
        if (newCount > 0) {
            if (badge) {
                badge.textContent = newCount;
            } else {
                badge = document.createElement("span");
                badge.className = "unread-badge";
                badge.textContent = newCount;
                chatItem.appendChild(badge);
            }
        } else {
            if (badge) {
                badge.remove();
            }
        }
    }
    // Update in online friends container
    const onlineItem = document.getElementById(friendId);
    if (onlineItem) {
        let badge = onlineItem.querySelector(".unread-badge");
        if (newCount > 0) {
            if (badge) {
                badge.textContent = newCount;
            } else {
                badge = document.createElement("span");
                badge.className = "unread-badge";
                badge.textContent = newCount;
                onlineItem.appendChild(badge);
            }
        } else {
            if (badge) {
                badge.remove();
            }
        }
    }
}

// Remove unread badge (set to 0) for a friend in both views
function removeUnreadBadge(friendId) {
    updateUnreadBadge(friendId, 0);
}

// ----- Load Friends (Chat List) -----
function loadFriends() {
    fetch("/api/friends")
        .then(response => response.json())
        .then(friends => {
            const chatList = document.getElementById("chat-list");
            if (!chatList) {
                console.error("Element with id 'chat-list' not found.");
                return;
            }
            chatList.innerHTML = "";
            // Sort friends: unread messages first, then online status
            friends.sort((a, b) => {
                if (b.unread_count !== a.unread_count) {
                    return b.unread_count - a.unread_count;
                }
                return b.is_online - a.is_online;
            });
            friends.forEach(friend => {
                const listItem = document.createElement("li");
                // Set custom data attribute to identify the friend
                listItem.setAttribute("data-friend-id", friend.custom_id);
                listItem.setAttribute("data-unread", friend.unread_count);
                listItem.innerHTML = `
                    <div class="chat-avatar" style="position: relative">
                        <img src="${friend.profile_picture || currentUser.default_avater}" alt="${friend.username}">
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
                listItem.onclick = () => { 
                    selectChat(friend.custom_id, friend.username, friend.is_online);
                };
                chatList.appendChild(listItem);
            });
        })
        .catch(error => console.error("Error loading friends:", error));
}

// ----- Load Online Friends -----
function loadOnlineFriends() {
    fetch("/api/friends")
        .then(response => response.json())
        .then(friends => {
            // Filter for online friends only
            let onlineFriends = friends.filter(friend => friend.is_online);
            // Sort online friends by unread count descending
            onlineFriends.sort((a, b) => b.unread_count - a.unread_count);
            
            const onlineFriendsContainer = document.getElementById("online-friends");
            if (!onlineFriendsContainer) {
                console.error("Element with id 'online-friends' not found.");
                return;
            }
            onlineFriendsContainer.innerHTML = "";
            
            onlineFriends.forEach(friend => {
                const friendDiv = document.createElement("div");
                friendDiv.classList.add("friend-item");
                // Set id so we can later update its unread badge easily
                friendDiv.id = friend.custom_id;
                friendDiv.style.display = "inline-block";
                friendDiv.style.position = "relative";
                friendDiv.style.cursor = "pointer";
                friendDiv.innerHTML = `
                    <img src="${friend.profile_picture || currentUser.default_avater}" 
                         alt="${friend.username}" 
                         title="${friend.username}" 
                         style="width:50px;height:50px;border-radius:50%;">
                    <!-- Online indicator -->
                    <div class="online-indicator" 
                         style="position: absolute; bottom: 4px; right: 4px; width: 10px; height: 10px; background-color: green; border: 2px solid white; border-radius: 50%;">
                    </div>
                    ${friend.unread_count > 0 ? `<span class="unread-badge" 
                        style="position: absolute; top: 0; right: 0; background: lightgreen; color: white; border-radius: 50%; padding: 1px 4px; font-size: 12px;">
                        ${friend.unread_count}
                    </span>` : ''}
                `;
                friendDiv.onclick = () => {
                    selectChat(friend.custom_id, friend.username, friend.is_online);
                };
                onlineFriendsContainer.appendChild(friendDiv);
            });
        })
        .catch(error => console.error("Error loading online friends:", error));
}

// ----- Select Chat & Load Messages -----
function selectChat(friendId, friendName, friend_status) {
    const user_status = friend_status ? 'online' : 'offline';
    document.getElementById("chat-header-name").innerText = friendName;
    document.getElementById("chat-header-name").setAttribute("data-receiver-id", friendId);
    document.getElementById("chat-header-status").innerText = user_status;
    document.getElementById("message-input").disabled = false;
    document.getElementById("send-button").disabled = false;
    
    // Remove unread badges and mark messages as read on backend
    removeUnreadBadge(friendId);
    fetch(`/api/mark_as_read/${friendId}`, { method: "POST" })
        .then(() => {
            // Reload friend lists to update unread counts
            loadFriends();
            loadOnlineFriends();
        })
        .catch(error => console.error("Error marking messages as read:", error));
    
    // Load chat messages for this friend
    fetch(`/api/messages/${friendId}`)
        .then(response => response.json())
        .then(messages => {
            const chatMessages = document.getElementById("chat-messages");
            chatMessages.innerHTML = "";
            messages.forEach(msg => {
                const isCurrentUser = msg.sender_id === currentUser.custom_id;
                appendMessage(friendName, msg.message_text, msg.timestamp, isCurrentUser);
            });
            if (window.innerWidth <= 768) {
                const sidebar = document.querySelector('.sidebar');
                if (sidebar.classList.contains('active')) {
                  toggleSidebar();
                }
            }
        })
        .catch(error => console.error("Error loading messages:", error));
}

function appendMessage(sender, text, timestamp, isCurrentUser) {
    const chatMessages = document.getElementById("chat-messages");
    const messageElement = document.createElement("div");
    messageElement.classList.add("message", isCurrentUser ? "sent" : "received");
    messageElement.innerHTML = `
        <div class="message-content">
             ${text}
            <div class="message-timestamp">${timestamp}</div>
        </div>
    `;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ----- Sort Chat List (if needed) -----
function sortChatList() {
    const chatList = document.getElementById("chat-list");
    const items = Array.from(chatList.children);
    items.sort((a, b) => {
        const aUnread = parseInt(a.getAttribute("data-unread")) || 0;
        const bUnread = parseInt(b.getAttribute("data-unread")) || 0;
        const aOnline = a.querySelector(".online-dot") ? 1 : 0;
        const bOnline = b.querySelector(".online-dot") ? 1 : 0;
        
        const aTimeElement = a.querySelector(".chat-preview");
        const bTimeElement = b.querySelector(".chat-preview");
        const aTimestamp = aTimeElement ? aTimeElement.textContent : "";
        const bTimestamp = bTimeElement ? bTimeElement.textContent : "";
        
        if (bUnread !== aUnread) return bUnread - aUnread;
        if (bOnline !== aOnline) return bOnline - aOnline;
        return bTimestamp.localeCompare(aTimestamp);
    });
    items.forEach(item => chatList.appendChild(item));
}

// ----- Real-Time Updates with Socket.IO -----
socket.on("update_status", (data) => {
    loadFriends();
    loadOnlineFriends();
});

socket.on("receive_message", data => {
    const currentChatId = document.getElementById("chat-header-name")?.dataset.receiverId;
    const isCurrentChat = data.sender_id === currentChatId;
    
    // If the message belongs to the active chat, append it
    if (data.receiver_id === currentUser.custom_id && isCurrentChat) {
        const isCurrentUser = data.sender_id === currentUser.custom_id;
        appendMessage(data.sender_name, data.message_text, data.timestamp, isCurrentUser);
    }
    
    // For messages not in the active chat, update unread badges in both views
    if (data.receiver_id === currentUser.custom_id && !isCurrentChat) {
        const chatItem = document.querySelector(`#chat-list li[data-friend-id="${data.sender_id}"]`);
        let currentCount = 0;
        if (chatItem) {
            currentCount = parseInt(chatItem.getAttribute("data-unread")) || 0;
        }
        const newCount = currentCount + 1;
        updateUnreadBadge(data.sender_id, newCount);
        sortChatList();
    }
});

// ----- Friend Request Functions -----
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
        headers: { "Content-Type": "application/json" }
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
        headers: { "Content-Type": "application/json" }
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

// ----- Search Users for Friend -----
function searchUsersForFriend() {
    const searchQuery = document.getElementById("search-friend").value;
    fetch(`/api/search_users?query=${searchQuery}`)
        .then(response => response.json())
        .then(data => {
            const friendList = document.getElementById("friend-list");
            friendList.innerHTML = "";
            data.forEach(user => {
                const isRequestSent = user.request_status == "none";
                const buttonText = isRequestSent ? "Request Sent" : "Add Friend";
                const disabledAttr = isRequestSent ? "disabled" : "";
                const listItem = document.createElement("li");
                listItem.innerHTML = `
                    <div class="user-avatar">
                        <img src="${user.profile_picture || currentUser.default_avater}" alt="${user.username}">
                    </div>
                    <div class="user-details">
                        <div class="user-name">${user.username}</div>
                        ${user.mutual_friends > 0 ? `<div class="mutual-friends">${user.mutual_friends} mutual friend${user.mutual_friends !== 1 ? "s" : ""}</div>` : '<div class="no-mutual">No mutual friends</div>'}
                    </div>
                    <button class="btn bg-success" onclick="sendFriendRequest('${user.custom_id}')" id="${user.custom_id}" ${disabledAttr}>
                        ${buttonText}
                    </button>
                `;
                friendList.appendChild(listItem);
            });
        })
        .catch(error => console.error("Error searching users for friend:", error));
}

// ----- Send Friend Request -----
function sendFriendRequest(receiverId) {
    fetch('/api/friend_request', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ receiver_id: receiverId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Friend request sent!");
            document.getElementById(receiverId).remove();
        } else {
            alert("Error: " + data.error);
        }
    });
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
        body: JSON.stringify({ receiver_id: receiverId, message: messageText })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            appendMessage("Me", messageText, new Date().toLocaleTimeString(), true);
            messageInput.value = "";
        } else {
            alert("Error: " + data.error);
        }
    })
    .catch(error => console.error("Error sending message:", error));
});

// ----- DOMContentLoaded -----
document.addEventListener("DOMContentLoaded", () => {
    openTab("chats");
    loadFriends();
    loadOnlineFriends();
    loadFriendRequests();
});
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    sidebar.classList.toggle('active');
    if (window.innerWidth <= 768 && !sidebar.classList.contains('active')) {
        document.querySelector('.main-chat').style.display = 'flex';
      } else {
        document.querySelector('.main-chat').style.display = 'none';
    }
}

// In script.js

// ✅ Listen for real-time profile updates
socket.on("profile_updated", (data) => {
    console.log("Profile updated in real-time:", data);

    // ✅ Update current user profile if it matches
    if (currentUser.custom_id === data.user_id) {
        currentUser.username = data.username;
        currentUser.profile_picture = "/" + data.profile_picture; // Ensure proper path
        document.getElementById("profile-preview").src = currentUser.profile_picture;
        document.getElementById("profile-username").value = currentUser.username;
    }

    // ✅ Update user in friend lists
    const friendItems = document.querySelectorAll(".friend-item");
    friendItems.forEach(item => {
        if (item.id === data.user_id) {
            const img = item.querySelector("img");
            if (img) img.src = "/" + data.profile_picture; // Update image in friend list
        }
    });

    // ✅ Refresh UI
    loadFriends();
    loadOnlineFriends();
});
function previewProfileImage() {
    const preview = document.getElementById('profile-preview');
    const fileInput = document.getElementById('profile-picture');
    const file = fileInput.files[0];
  
    if (file) {
      const reader = new FileReader();
  
      reader.onload = function () {
        preview.src = reader.result;
      };
  
      reader.readAsDataURL(file);
    }
  }
  
  async function updateProfile(event) {
    event.preventDefault(); // Prevent default form submission
  
    const form = document.getElementById('profile-form');
    const formData = new FormData(form);
    const profilePicture = document.getElementById('profile-picture').files[0];
  
    if(profilePicture){
      formData.append('profile_picture', profilePicture);
    }
  
    try {
      const response = await fetch('/api/update_profile', { // Replace '/update_profile' with your actual endpoint
        method: 'POST',
        body: formData,
      });
  
      if (response.ok) {
        // Profile updated successfully
        alert('Profile updated successfully!');
        // Optionally, you can reload the page or update the UI
        //window.location.reload(); //reload the page.
      } else {
        // Handle error
        const errorData = await response.json();
        alert('Failed to update profile: ' + (errorData.message || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error updating profile:', error);
      alert('An error occurred while updating profile.');
    }
  }
  
  function logout() {
    fetch("/logout", { 
        method: "POST",
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Disconnect Socket.IO
            if (socket) socket.disconnect()
            // Redirect to login
            window.location.href = "/"
        }
    })
    .catch(error => {
        console.error("Logout error:", error)
        window.location.href = "/"
    })
}
// Preview Image Before Upload

