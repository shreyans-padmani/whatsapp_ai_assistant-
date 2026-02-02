/**
 * Restaurant Booking Portal - Customer Interface
 */

class BookingChat {
    constructor() {
        this.messagesArea = document.getElementById('messagesArea');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.charCount = document.getElementById('charCount');

        // Generate unique user session ID
        this.userId = this.getOrCreateUserId();
        this.restaurantId = 'rest_001';

        // State
        this.isLoading = false;
        this.conversationHistory = [];

        // Initialize
        this.init();
    }

    init() {
        this.loadConversationHistory();
        this.attachEventListeners();
        this.autoResizeTextarea();
        this.showWelcomeMessage();
    }

    getOrCreateUserId() {
        let userId = localStorage.getItem('booking_user_id');
        if (!userId) {
            userId = `customer_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            localStorage.setItem('booking_user_id', userId);
        }
        return userId;
    }

    loadConversationHistory() {
        const stored = localStorage.getItem('booking_history');
        if (stored) {
            try {
                this.conversationHistory = JSON.parse(stored);
                this.renderConversationHistory();
            } catch (e) {
                console.error('Failed to load history:', e);
                this.conversationHistory = [];
            }
        }
    }

    saveConversationHistory() {
        try {
            localStorage.setItem('booking_history', JSON.stringify(this.conversationHistory));
        } catch (e) {
            console.error('Failed to save history:', e);
        }
    }

    renderConversationHistory() {
        if (this.conversationHistory.length > 0) {
            this.messagesArea.innerHTML = '';
            this.conversationHistory.forEach(msg => {
                this.addMessageToUI(
                    msg.role === 'user' ? 'outgoing' : 'incoming',
                    msg.content,
                    msg.timestamp
                );
            });
            this.scrollToBottom();
        }
    }

    showWelcomeMessage() {
        if (this.conversationHistory.length === 0) {
            const welcomeHTML = `
                <div class="welcome-message">
                    <div class="welcome-card">
                        <div class="welcome-icon">
                            <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <circle cx="32" cy="32" r="30" fill="#25D366" opacity="0.1"/>
                                <circle cx="32" cy="32" r="24" fill="#25D366"/>
                                <path d="M42 25c-1.7-3-4.4-5.4-7.6-6.8-3.2-1.4-6.9-1.7-10.3-.8-3.4.9-6.4 2.8-8.5 5.5-2.1 2.7-3.3 6-3.3 9.4 0 2.5.6 4.9 1.8 7l-1.9 7 7.2-1.9c2 1.1 4.3 1.6 6.6 1.6 3.4 0 6.6-1.2 9.2-3.3 2.6-2.1 4.4-5 5.2-8.3.8-3.2.5-6.7-.4-9.4zm-10.6 19.5c-2.1 0-4.2-.5-6-1.5l-.4-.3-4.4 1.2 1.2-4.3-.3-.5c-1.1-1.9-1.6-4-1.6-6.2 0-6.6 5.4-12 12-12s12 5.4 12 12-5.3 11.6-12.5 11.6z" fill="white"/>
                            </svg>
                        </div>
                        <h2>Welcome to Our Restaurant!</h2>
                        <p>Book your table easily through our AI assistant</p>
                        <ul class="feature-list">
                            <li>
                                <svg viewBox="0 0 20 20" fill="currentColor">
                                    <path d="M10 0C4.48 0 0 4.48 0 10C0 15.52 4.48 20 10 20C15.52 20 20 15.52 20 10C20 4.48 15.52 0 10 0ZM8 14.5L3.5 10L4.91 8.59L8 11.67L15.09 4.58L16.5 6L8 14.5Z"/>
                                </svg>
                                Check available time slots
                            </li>
                            <li>
                                <svg viewBox="0 0 20 20" fill="currentColor">
                                    <path d="M10 0C4.48 0 0 4.48 0 10C0 15.52 4.48 20 10 20C15.52 20 20 15.52 20 10C20 4.48 15.52 0 10 0ZM8 14.5L3.5 10L4.91 8.59L8 11.67L15.09 4.58L16.5 6L8 14.5Z"/>
                                </svg>
                                Instant booking confirmation
                            </li>
                            <li>
                                <svg viewBox="0 0 20 20" fill="currentColor">
                                    <path d="M10 0C4.48 0 0 4.48 0 10C0 15.52 4.48 20 10 20C15.52 20 20 15.52 20 10C20 4.48 15.52 0 10 0ZM8 14.5L3.5 10L4.91 8.59L8 11.67L15.09 4.58L16.5 6L8 14.5Z"/>
                                </svg>
                                Manage your reservations
                            </li>
                        </ul>
                        <p class="cta-text">👇 Start chatting below to make your reservation!</p>
                    </div>
                </div>
            `;
            this.messagesArea.innerHTML = welcomeHTML;
        }
    }

    attachEventListeners() {
        // Input changes
        this.messageInput.addEventListener('input', () => {
            this.updateSendButton();
            this.updateCharCount();
            this.autoResizeTextarea();
        });

        // Send message on Enter (Shift+Enter for new line)
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSendMessage();
            }
        });

        // Send button click
        this.sendBtn.addEventListener('click', () => {
            this.handleSendMessage();
        });
    }

    async handleSendMessage() {
        const message = this.messageInput.value.trim();

        if (!message || this.isLoading) {
            return;
        }

        // Clear welcome message if present
        const welcomeMsg = this.messagesArea.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => welcomeMsg.remove(), 300);
        }

        // Add user message
        const timestamp = new Date();
        this.addMessageToUI('outgoing', message, timestamp);
        this.conversationHistory.push({
            role: 'user',
            content: message,
            timestamp: timestamp.toISOString()
        });
        this.saveConversationHistory();

        // Clear input
        this.messageInput.value = '';
        this.updateSendButton();
        this.updateCharCount();
        this.resetTextareaHeight();

        // Show typing indicator
        this.showTypingIndicator();

        // Send to API
        await this.sendMessageToAPI(message);
    }

    async sendMessageToAPI(message) {
        const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message_id: messageId,
                    restaurant_id: this.restaurantId,
                    contact_number: this.userId,
                    message: message
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Remove typing indicator
            this.hideTypingIndicator();

            // Add assistant response
            const timestamp = new Date();
            this.addMessageToUI('incoming', data.response, timestamp);
            this.conversationHistory.push({
                role: 'assistant',
                content: data.response,
                timestamp: timestamp.toISOString()
            });
            this.saveConversationHistory();

        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();

            // Show error message
            this.addMessageToUI(
                'incoming',
                `Sorry, I couldn't process your request. Please try again or contact us directly.`,
                new Date()
            );
        }
    }

    addMessageToUI(type, text, timestamp) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        const time = this.formatTime(timestamp);

        const bubbleHTML = `
            <div class="message-bubble">
                <div class="message-text">${this.escapeHtml(text).replace(/\n/g, '<br>')}</div>
                <div class="message-meta">
                    <span class="message-time">${time}</span>
                    ${type === 'outgoing' ? '<svg class="checkmark" viewBox="0 0 16 15"><path fill="currentColor" d="M15.01 3.316l-.478-.372a.365.365 0 0 0-.51.063L8.666 9.879a.32.32 0 0 1-.484.033l-.358-.325a.319.319 0 0 0-.484.032l-.378.483a.418.418 0 0 0 .036.541l1.32 1.266c.143.14.361.125.484-.033l6.272-8.048a.366.366 0 0 0-.064-.512zm-4.1 0l-.478-.372a.365.365 0 0 0-.51.063L4.566 9.879a.32.32 0 0 1-.484.033L1.891 7.769a.366.366 0 0 0-.515.006l-.423.433a.364.364 0 0 0 .006.514l3.258 3.185c.143.14.361.125.484-.033l6.272-8.048a.365.365 0 0 0-.063-.51z"></path></svg>' : ''}
                </div>
            </div>
        `;

        messageDiv.innerHTML = bubbleHTML;
        this.messagesArea.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showTypingIndicator() {
        this.isLoading = true;
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message incoming typing-message';
        typingDiv.innerHTML = `
            <div class="message-bubble loading-bubble">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        this.messagesArea.appendChild(typingDiv);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.isLoading = false;
        const typingMsg = this.messagesArea.querySelector('.typing-message');
        if (typingMsg) {
            typingMsg.remove();
        }
    }

    updateSendButton() {
        const hasContent = this.messageInput.value.trim().length > 0;
        if (hasContent) {
            this.sendBtn.classList.add('active');
        } else {
            this.sendBtn.classList.remove('active');
        }
    }

    updateCharCount() {
        const count = this.messageInput.value.length;
        this.charCount.textContent = count;
    }

    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        const newHeight = Math.min(this.messageInput.scrollHeight, 100);
        this.messageInput.style.height = newHeight + 'px';
    }

    resetTextareaHeight() {
        this.messageInput.style.height = 'auto';
    }

    scrollToBottom() {
        requestAnimationFrame(() => {
            this.messagesArea.parentElement.scrollTop = this.messagesArea.parentElement.scrollHeight;
        });
    }

    formatTime(timestamp) {
        const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
        let hours = date.getHours();
        const minutes = date.getMinutes();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12;
        hours = hours ? hours : 12;
        const minutesStr = minutes < 10 ? '0' + minutes : minutes;
        return `${hours}:${minutesStr} ${ampm}`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Add fadeOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        from {
            opacity: 1;
            transform: scale(1);
        }
        to {
            opacity: 0;
            transform: scale(0.95);
        }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.bookingChat = new BookingChat();
});
