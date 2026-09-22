/* =========================================================================
   NexCart AI Chatbot — JavaScript Controller
   ========================================================================= */

document.addEventListener('DOMContentLoaded', function () {

    // ── DOM References ──
    const toggleBtn   = document.getElementById('chatbot-toggle');
    const closeBtn    = document.getElementById('chatbot-close');
    const backBtn     = document.getElementById('chatbot-back');
    const clearBtn    = document.getElementById('chatbot-clear');
    const chatWindow  = document.getElementById('chatbot-window');
    const messagesEl  = document.getElementById('chatbot-messages');
    const inputEl     = document.getElementById('chatbot-input');
    const sendBtn     = document.getElementById('chatbot-send');
    const typingEl    = document.getElementById('chatbot-typing');
    const statusText  = document.getElementById('chatbot-status-text');
    const charCount   = document.getElementById('chatbot-char-count');
    const welcomeEl   = document.getElementById('chatbot-welcome');
    const quickActEl  = document.getElementById('chatbot-quick-actions');
    const statusDot   = document.querySelector('.chatbot-status-dot');

    // Bail out if required elements are missing
    if (!toggleBtn || !chatWindow || !messagesEl || !inputEl || !sendBtn) return;

    // ── State ──
    let isSending = false;
    let isApiAvailable = true;

    // ── Helpers ──

    function getCookie(name) {
        let value = null;
        if (document.cookie && document.cookie !== '') {
            for (let part of document.cookie.split(';')) {
                part = part.trim();
                if (part.startsWith(name + '=')) {
                    value = decodeURIComponent(part.substring(name.length + 1));
                    break;
                }
            }
        }
        return value;
    }

    function scrollToBottom() {
        requestAnimationFrame(function () {
            messagesEl.scrollTop = messagesEl.scrollHeight;
        });
    }

    function formatTime() {
        const now = new Date();
        return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function setUnavailableState() {
        isApiAvailable = false;
        if (statusText) statusText.textContent = 'Chatbot temporarily unavailable';
        if (statusDot) {
            statusDot.style.background = '#EF4444'; // Red
            statusDot.style.boxShadow = '0 0 8px rgba(239, 68, 68, 0.6)';
            statusDot.style.animation = 'none'; // Stop glowing
        }
        inputEl.placeholder = 'Chatbot is currently unavailable...';
    }

    function setAvailableState() {
        isApiAvailable = true;
        if (statusText) statusText.textContent = 'Online \u2022 Ready to help';
        if (statusDot) {
            statusDot.style.background = '#34D399'; // Green
            statusDot.style.boxShadow = '0 0 8px rgba(52, 211, 153, 0.6)';
            statusDot.style.animation = 'chatbot-dot-glow 2s ease-in-out infinite alternate';
        }
        inputEl.placeholder = 'Ask NexCart Chatbot anything...';
    }

    // ── Health Check ──
    async function checkHealth() {
        try {
            const res = await fetch('/chatbot/health/');
            if (!res.ok) throw new Error('Health check failed');
            const data = await res.json();
            if (data.status !== 'ok') {
                setUnavailableState();
            } else {
                setAvailableState();
            }
        } catch (err) {
            console.warn('NexCart Chatbot: Health check failed.', err);
            // Default to unavailable if we can't even reach the health endpoint
            setUnavailableState();
        }
    }

    // Run health check on load
    checkHealth();

    // ── Toggle Window ──

    toggleBtn.addEventListener('click', function () {
        const isOpen = chatWindow.classList.toggle('active');
        toggleBtn.classList.toggle('is-open', isOpen);

        if (isOpen) {
            inputEl.focus();
            scrollToBottom();
            // Re-check health on open just to be sure
            checkHealth();
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', function () {
            chatWindow.classList.remove('active');
            toggleBtn.classList.remove('is-open');
        });
    }

    if (backBtn) {
        backBtn.addEventListener('click', function () {
            // Remove all chat messages but keep the welcome + quick actions
            messagesEl.querySelectorAll('.chat-message').forEach(function (el) {
                el.remove();
            });

            // Re-show welcome and chips
            if (welcomeEl)  welcomeEl.style.display = '';
            if (quickActEl) quickActEl.style.display = '';

            if (isApiAvailable) {
                setAvailableState();
            }
        });
    }

    // ── Clear Chat ──

    if (clearBtn) {
        clearBtn.addEventListener('click', function () {
            // Remove all chat messages but keep the welcome + quick actions
            messagesEl.querySelectorAll('.chat-message').forEach(function (el) {
                el.remove();
            });

            // Re-show welcome and chips
            if (welcomeEl)  welcomeEl.style.display = '';
            if (quickActEl) quickActEl.style.display = '';

            if (isApiAvailable) {
                setAvailableState();
            }
        });
    }

    // ── Character Counter ──

    if (charCount) {
        inputEl.addEventListener('input', function () {
            charCount.textContent = inputEl.value.length + ' / 2000';
        });
    }

    // ── Quick Action Chips ──

    if (quickActEl) {
        quickActEl.addEventListener('click', function (e) {
            const chip = e.target.closest('.chatbot-chip');
            if (!chip) return;

            const message = chip.getAttribute('data-message');
            if (message) {
                inputEl.value = message;
                sendMessage();
            }
        });
    }

    // ── Add Message to UI ──

    function addMessage(text, type) {
        // Hide welcome & quick actions after first message
        if (welcomeEl)  welcomeEl.style.display  = 'none';
        if (quickActEl) quickActEl.style.display  = 'none';

        const wrapper = document.createElement('div');
        wrapper.className = 'chat-message ' + (type === 'user' ? 'user-message' : 'bot-message');
        if (type === 'error') {
            wrapper.className = 'chat-message bot-message error-message';
        }

        const content = document.createElement('div');
        content.className = 'message-content';
        content.textContent = text;

        // Timestamp
        const time = document.createElement('span');
        time.className = 'message-time';
        time.textContent = formatTime();
        content.appendChild(time);

        wrapper.appendChild(content);
        messagesEl.appendChild(wrapper);
        scrollToBottom();
    }

    // ── Typing Indicator ──

    function showTyping() {
        if (typingEl) {
            typingEl.classList.add('active');
            scrollToBottom();
        }
        if (statusText) statusText.textContent = 'Thinking\u2026';
    }

    function hideTyping() {
        if (typingEl) typingEl.classList.remove('active');
        if (isApiAvailable) {
            setAvailableState();
        } else {
            setUnavailableState();
        }
    }

    // ── Send Message ──

    async function sendMessage() {
        const message = inputEl.value.trim();
        if (!message || isSending) return;

        isSending = true;
        sendBtn.disabled = true;

        addMessage(message, 'user');
        inputEl.value = '';
        if (charCount) charCount.textContent = '0 / 2000';

        showTyping();

        try {
            const response = await fetch('/chatbot/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ message: message }),
            });

            const data = await response.json();
            hideTyping();

            if (response.ok && data.success) {
                setAvailableState();
                addMessage(data.response, 'bot');
            } else {
                if (response.status === 503) {
                    setUnavailableState();
                }
                addMessage(data.error || 'Sorry, something went wrong. Please try again.', 'error');
            }
        } catch (err) {
            hideTyping();
            setUnavailableState();
            addMessage("Sorry, I couldn't connect to NexCart Chatbot right now. Please try again.", 'error');
            console.error('NexCart Chatbot fetch error:', err);
        } finally {
            isSending = false;
            sendBtn.disabled = false;
            inputEl.focus();
        }
    }

    // ── Event Listeners ──

    sendBtn.addEventListener('click', sendMessage);

    inputEl.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Close on outside click
    document.addEventListener('click', function (e) {
        if (
            chatWindow.classList.contains('active') &&
            !chatWindow.contains(e.target) &&
            !toggleBtn.contains(e.target)
        ) {
            chatWindow.classList.remove('active');
            toggleBtn.classList.remove('is-open');
        }
    });

    // Close on Escape
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && chatWindow.classList.contains('active')) {
            chatWindow.classList.remove('active');
            toggleBtn.classList.remove('is-open');
        }
    });

});
