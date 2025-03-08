document.addEventListener('DOMContentLoaded', function () {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');

    sendButton.addEventListener('click', function () {
        const message = messageInput.value.trim();
        if (message) {
            // Send the message to the server (you'll need to implement this)
            sendMessage(message);

            // Clear the input field
            messageInput.value = '';
        }
    });

    function sendMessage(message) {
        // Simulate sending a message (replace with actual API call)
        const messageElement = document.createElement('div');
        messageElement.textContent = message;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Auto-scroll to the bottom
    }
});