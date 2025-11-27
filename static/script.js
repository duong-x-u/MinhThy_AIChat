// ========== SOCKET CONNECTION ==========
const socket = io({ path: '/duongdev/minhthy/socket.io' });

// ========== DOM ELEMENTS ==========
const elements = {
    // Sidebar
    sidebar: document.getElementById('sidebar'),
    conversationList: document.getElementById('conversationList'),
    newChatBtn: document.getElementById('newChatBtn'),
    menuToggle: document.getElementById('menuToggle'),
    
    // Theme & Sound
    themeToggle: document.getElementById('themeToggle'),
    soundToggle: document.getElementById('soundToggle'),
    
    // Header
    aiNickname: document.getElementById('aiNickname'),
    avatarLetter: document.getElementById('avatarLetter'),
    statusText: document.getElementById('statusText'),
    startName: document.getElementById('startName'),
    
    // Search
    searchBtn: document.getElementById('searchBtn'),
    searchBar: document.getElementById('searchBar'),
    searchInput: document.getElementById('searchInput'),
    closeSearch: document.getElementById('closeSearch'),
    searchResults: document.getElementById('searchResults'),
    
    // Chat
    chatArea: document.getElementById('chatArea'),
    scrollBottomBtn: document.getElementById('scrollBottomBtn'),
    typingIndicator: document.getElementById('typingIndicator'),
    
    // Reply
    replyPreview: document.getElementById('replyPreview'),
    replySender: document.getElementById('replySender'),
    replyText: document.getElementById('replyText'),
    cancelReply: document.getElementById('cancelReply'),
    
    // Input
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn'),
    emojiBtn: document.getElementById('emojiBtn'),
    emojiPicker: document.getElementById('emojiPicker'),
    
    // Modals
    settingsBtn: document.getElementById('settingsBtn'),
    settingsModal: document.getElementById('settingsModal'),
    closeSettings: document.getElementById('closeSettings'),
    saveSettings: document.getElementById('saveSettings'),
    
    exportBtn: document.getElementById('exportBtn'),
    exportModal: document.getElementById('exportModal'),
    closeExport: document.getElementById('closeExport'),
    exportTxt: document.getElementById('exportTxt'),
    exportJson: document.getElementById('exportJson'),
    
    // Settings inputs
    convNameInput: document.getElementById('convNameInput'),
    aiNameInput: document.getElementById('aiNameInput'),
    userNameInput: document.getElementById('userNameInput'),
    moodSlider: document.getElementById('moodSlider'),
    moodValue: document.getElementById('moodValue'),
    messageCount: document.getElementById('messageCount'),
    deleteConvBtn: document.getElementById('deleteConvBtn'),
    
    // Reactions
    reactionPicker: document.getElementById('reactionPicker'),
    
    // Audio
    notificationSound: document.getElementById('notificationSound')
};

// ========== STATE ==========
let state = {
    currentConversationId: null,
    conversations: [],
    settings: {},
    replyToMessage: null,
    soundEnabled: true,
    isConnected: false
};

// ========== SOCKET EVENTS ==========
socket.on('connect', () => {
    state.isConnected = true;
    elements.statusText.textContent = 'Đang online';
    elements.statusText.style.color = 'var(--success)';
    console.log('✅ Connected');
});

socket.on('disconnect', () => {
    state.isConnected = false;
    elements.statusText.textContent = 'Mất kết nối...';
    elements.statusText.style.color = 'var(--danger)';
});

socket.on('init_data', (data) => {
    state.settings = data.settings;
    state.conversations = data.conversations;
    
    if (data.current_conversation) {
        state.currentConversationId = data.current_conversation.id;
        updateHeader(data.current_conversation);
        updateSettingsModal(data.current_conversation);
    }
    
    elements.messageCount.textContent = data.message_count;
    
    // Apply settings
    applyTheme(state.settings.theme || 'dark');
    applySoundSetting(state.settings.sound_enabled !== 'false');
    
    renderConversations();
    renderMessages(data.messages);
    scrollToBottom(false);
});

socket.on('conversation_switched', (data) => {
    state.currentConversationId = data.conversation.id;
    updateHeader(data.conversation);
    updateSettingsModal(data.conversation);
    elements.messageCount.textContent = data.message_count;
    
    renderMessages(data.messages);
    scrollToBottom(false);
    closeSidebar();
});

socket.on('conversation_created', (data) => {
    state.conversations = data.conversations;
    state.currentConversationId = data.conversation.id;
    
    renderConversations();
    updateHeader(data.conversation);
    updateSettingsModal(data.conversation);
    renderMessages([]);
    closeSidebar();
});

socket.on('conversation_deleted', (data) => {
    state.conversations = data.conversations;
    state.currentConversationId = data.switch_to.id;
    
    renderConversations();
    updateHeader(data.switch_to);
    updateSettingsModal(data.switch_to);
    renderMessages(data.messages);
    closeSidebar();
});

socket.on('conversation_updated', (data) => {
    state.conversations = data.conversations;
    updateHeader(data.conversation);
    renderConversations();
});

socket.on('conversations_updated', (data) => {
    state.conversations = data.conversations;
    renderConversations();
});

socket.on('message_sent', (data) => {
    // Cập nhật tin nhắn tạm thời với ID thật từ server
    const tempMessageElement = document.querySelector(`.message[data-id="${data.temp_id}"]`);
    if (tempMessageElement) {
        tempMessageElement.dataset.id = data.id; // Gán ID thật
    }
});

socket.on('typing_start', () => {
    elements.typingIndicator.classList.add('active');
    scrollToBottom();
});

socket.on('typing_stop', () => {
    elements.typingIndicator.classList.remove('active');
});

socket.on('new_message', (data) => {
    addMessageToUI('received', data);
    scrollToBottom();
    playNotificationSound();
    
    const count = parseInt(elements.messageCount.textContent) || 0;
    elements.messageCount.textContent = count + 1;
});

socket.on('reaction_updated', (data) => {
    updateMessageReactions(data.message_id, data.reactions);
});

socket.on('search_results', (data) => {
    renderSearchResults(data.results, data.query);
});

socket.on('setting_updated', (data) => {
    state.settings[data.key] = data.value;
    
    if (data.key === 'theme') {
        applyTheme(data.value);
    } else if (data.key === 'sound_enabled') {
        applySoundSetting(data.value === 'true');
    }
});

// ========== RENDER FUNCTIONS ==========
function renderConversations() {
    elements.conversationList.innerHTML = state.conversations.map(conv => `
        <div class="conversation-item ${conv.id === state.currentConversationId ? 'active' : ''}" 
             data-id="${conv.id}">
            <div class="conv-avatar">🌸</div>
            <div class="conv-info">
                <div class="conv-name">${escapeHtml(conv.name)}</div>
                <div class="conv-preview">${escapeHtml(conv.last_message || 'Chưa có tin nhắn')}</div>
            </div>
        </div>
    `).join('');
    
    // Click handlers
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.addEventListener('click', () => {
            const id = parseInt(item.dataset.id);
            if (id !== state.currentConversationId) {
                socket.emit('switch_conversation', { conversation_id: id });
            }
        });
    });
}

function renderMessages(messages) {
    if (!messages || messages.length === 0) {
        elements.chatArea.innerHTML = `
            <div class="chat-start-message">
                <div class="start-avatar">🌸</div>
                <p>Bắt đầu cuộc trò chuyện với <strong id="startName">${elements.aiNickname.textContent}</strong></p>
                <span class="start-hint">Lịch sử chat được lưu tự động</span>
            </div>
        `;
        return;
    }
    
    elements.chatArea.innerHTML = messages.map(msg => createMessageHTML(msg)).join('');
    
    // Add reaction handlers
    attachMessageHandlers();
}

function createMessageHTML(msg) {
    const type = msg.role === 'user' ? 'sent' : 'received';
    const reactions = parseReactions(msg.reactions);
    const time = formatTime(msg.timestamp);
    
    let replyHTML = '';
    if (msg.reply_content) {
        replyHTML = `
            <div class="msg-reply">
                <div class="msg-reply-sender">${escapeHtml(msg.reply_sender)}</div>
                <div class="msg-reply-text">${escapeHtml(msg.reply_content)}</div>
            </div>
        `;
    }
    
    let reactionsHTML = '';
    if (reactions.length > 0) {
        reactionsHTML = `
            <div class="message-reactions">
                ${reactions.map(r => `<span class="reaction-badge">${r}</span>`).join('')}
            </div>
        `;
    }
    
    const avatarHTML = type === 'received' ? `
        <div class="msg-avatar">${elements.avatarLetter.textContent}</div>
    ` : '';
    
    const seenHTML = type === 'sent' && msg.is_seen ? `<span class="message-seen">✓✓</span>` : '';
    
    return `
        <div class="message ${type}" data-id="${msg.id}">
            <div class="message-wrapper">
                ${avatarHTML}
                <div class="message-content">
                    ${replyHTML}
                    <div class="message-bubble">
                        <p class="message-text">${escapeHtml(msg.content)}</p>
                    </div>
                    <div class="message-meta">
                        <span class="message-time">${time}</span>
                        ${seenHTML}
                    </div>
                    ${reactionsHTML}
                </div>
            </div>
        </div>
    `;
}

function addMessageToUI(type, data) {
    // Remove start message if exists
    const startMsg = elements.chatArea.querySelector('.chat-start-message');
    if (startMsg) startMsg.remove();
    
    const msg = {
        id: data.id,
        role: type === 'sent' ? 'user' : 'assistant',
        sender_name: data.sender_name || (type === 'sent' ? state.settings.userName : elements.aiNickname.textContent),
        content: data.content,
        timestamp: data.timestamp,
        reply_content: data.reply_content,
        reply_sender: data.reply_sender,
        reactions: data.reactions || '[]',
        is_seen: data.is_seen || 0
    };
    
    const html = createMessageHTML(msg);
    elements.chatArea.insertAdjacentHTML('beforeend', html);
    
    // Attach handlers to new message
    attachMessageHandlers();
}

function attachMessageHandlers() {
    document.querySelectorAll('.message-bubble').forEach(bubble => {
        // Double click for reactions
        bubble.addEventListener('dblclick', (e) => {
            const msgEl = bubble.closest('.message');
            showReactionPicker(msgEl, e);
        });
        
        // Long press for reply (mobile)
        let pressTimer;
        bubble.addEventListener('touchstart', (e) => {
            pressTimer = setTimeout(() => {
                const msgEl = bubble.closest('.message');
                startReply(msgEl);
            }, 500);
        });
        
        bubble.addEventListener('touchend', () => {
            clearTimeout(pressTimer);
        });
        
        // Right click for reply (desktop)
        bubble.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            const msgEl = bubble.closest('.message');
            startReply(msgEl);
        });
    });
}

function renderSearchResults(results, query) {
    if (results.length === 0) {
        elements.searchResults.innerHTML = `<div class="no-results">Không tìm thấy kết quả cho "${escapeHtml(query)}"</div>`;
    } else {
        elements.searchResults.innerHTML = results.map(msg => {
            const highlighted = msg.content.replace(
                new RegExp(`(${escapeRegex(query)})`, 'gi'),
                '<mark>$1</mark>'
            );
            return `
                <div class="search-result-item" data-id="${msg.id}">
                    <div class="result-sender">${escapeHtml(msg.sender_name)}</div>
                    <div class="result-content">${highlighted}</div>
                </div>
            `;
        }).join('');
    }
    
    elements.searchResults.classList.add('active');
}

// ========== UI UPDATE FUNCTIONS ==========
function updateHeader(conv) {
    elements.aiNickname.textContent = conv.ai_name;
    elements.avatarLetter.textContent = conv.ai_name.charAt(0).toUpperCase();
    
    const startName = document.getElementById('startName');
    if (startName) startName.textContent = conv.ai_name;
}

function updateSettingsModal(conv) {
    elements.convNameInput.value = conv.name;
    elements.aiNameInput.value = conv.ai_name;
    elements.userNameInput.value = conv.user_name;
    elements.moodSlider.value = conv.mood;
    elements.moodValue.textContent = conv.mood;
}

// ========== REPLY FUNCTIONS ==========
function startReply(msgEl) {
    const msgId = parseInt(msgEl.dataset.id);
    const content = msgEl.querySelector('.message-text').textContent;
    const isSent = msgEl.classList.contains('sent');
    const senderName = isSent ? 'Bạn' : elements.aiNickname.textContent;
    
    state.replyToMessage = {
        id: msgId,
        content: content,
        sender: senderName
    };
    
    elements.replySender.textContent = senderName;
    elements.replyText.textContent = content.substring(0, 50) + (content.length > 50 ? '...' : '');
    elements.replyPreview.classList.add('active');
    
    elements.messageInput.focus();
}

function clearReply() {
    state.replyToMessage = null;
    elements.replyPreview.classList.remove('active');
}

// ========== REACTION FUNCTIONS ==========
function showReactionPicker(msgEl, event) {
    const picker = elements.reactionPicker;
    const rect = msgEl.getBoundingClientRect();
    
    picker.style.left = `${rect.left}px`;
    picker.style.top = `${rect.top - 50}px`;
    picker.classList.add('active');
    picker.dataset.messageId = msgEl.dataset.id;
    
    // Close on click outside
    setTimeout(() => {
        document.addEventListener('click', closeReactionPicker);
    }, 10);
}

function closeReactionPicker() {
    elements.reactionPicker.classList.remove('active');
    document.removeEventListener('click', closeReactionPicker);
}

function updateMessageReactions(msgId, reactions) {
    const msgEl = document.querySelector(`.message[data-id="${msgId}"]`);
    if (!msgEl) return;
    
    let reactionsContainer = msgEl.querySelector('.message-reactions');
    
    if (reactions.length === 0) {
        if (reactionsContainer) reactionsContainer.remove();
        return;
    }
    
    const html = reactions.map(r => `<span class="reaction-badge">${r}</span>`).join('');
    
    if (reactionsContainer) {
        reactionsContainer.innerHTML = html;
    } else {
        const meta = msgEl.querySelector('.message-meta');
        meta.insertAdjacentHTML('afterend', `<div class="message-reactions">${html}</div>`);
    }
}

// ========== THEME & SOUND ==========
function applyTheme(theme) {
    document.body.classList.remove('dark-theme', 'light-theme');
    document.body.classList.add(`${theme}-theme`);
}

function applySoundSetting(enabled) {
    state.soundEnabled = enabled;
    document.body.dataset.sound = enabled.toString();
}

function playNotificationSound() {
    if (state.soundEnabled && elements.notificationSound) {
        elements.notificationSound.currentTime = 0;
        elements.notificationSound.play().catch(() => {});
    }
}

// ========== UTILITY FUNCTIONS ==========
function formatTime(timestamp) {
    if (!timestamp) return '';
    
    try {
        // Parse timestamp dạng "2024-01-15 10:30:00"
        let date;
        
        if (timestamp.includes(' ') && !timestamp.includes('T')) {
            // Format: "2024-01-15 10:30:00" -> convert to ISO
            date = new Date(timestamp.replace(' ', 'T') + '+07:00');
        } else if (timestamp.includes('T')) {
            // Already ISO format
            date = new Date(timestamp);
        } else {
            // Just time like "10:30"
            return timestamp;
        }
        
        // Check if valid date
        if (isNaN(date.getTime())) {
            return timestamp; // Return original if can't parse
        }
        
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        // Nếu trong tương lai hoặc vừa xong
        if (diffMins < 1) return 'Vừa xong';
        if (diffMins < 60) return `${diffMins} phút trước`;
        if (diffHours < 24) return `${diffHours} giờ trước`;
        if (diffDays < 7) return `${diffDays} ngày trước`;
        
        // Format ngày tháng
        return date.toLocaleString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit',
            day: '2-digit',
            month: '2-digit'
        });
    } catch (e) {
        console.error('Error parsing time:', e, timestamp);
        return timestamp || '';
    }
}

function parseReactions(reactions) {
    if (!reactions) return [];
    try {
        return JSON.parse(reactions);
    } catch {
        return [];
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function scrollToBottom(smooth = true) {
    setTimeout(() => {
        elements.chatArea.scrollTo({
            top: elements.chatArea.scrollHeight,
            behavior: smooth ? 'smooth' : 'auto'
        });
    }, 50);
}

function closeSidebar() {
    elements.sidebar.classList.remove('open');
}

// ========== AUTO-RESIZE TEXTAREA ==========
function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

// ========== SEND MESSAGE ==========
function sendMessage() {
    const messageContent = elements.messageInput.value.trim();
    if (!messageContent || !state.isConnected || !state.currentConversationId) return;

    const tempId = `temp_${Date.now()}`;
    const now = new Date();
    const timestamp = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    
    const messageData = {
        id: tempId,
        role: 'user',
        content: messageContent,
        timestamp: timestamp,
        reply_to_id: state.replyToMessage?.id || null,
        reply_content: state.replyToMessage?.content || null,
        reply_sender: state.replyToMessage?.sender || null,
    };

    addMessageToUI('sent', messageData);
    scrollToBottom();
    
    socket.emit('send_message', {
        conversation_id: state.currentConversationId,
        message: messageContent,
        reply_to_id: state.replyToMessage?.id || null,
        temp_id: tempId
    });
    
    clearReply();
    elements.messageInput.value = '';
    elements.messageInput.style.height = 'auto';
    elements.messageInput.focus();
}

// ========== EVENT LISTENERS ==========

// Send message
elements.sendBtn.addEventListener('click', sendMessage);
elements.messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});
elements.messageInput.addEventListener('input', () => autoResize(elements.messageInput));

// Reply
elements.cancelReply.addEventListener('click', clearReply);

// Emoji picker
elements.emojiBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    elements.emojiPicker.classList.toggle('active');
});

document.querySelectorAll('.emoji-grid span').forEach(emoji => {
    emoji.addEventListener('click', () => {
        elements.messageInput.value += emoji.textContent;
        elements.emojiPicker.classList.remove('active');
        elements.messageInput.focus();
    });
});

document.addEventListener('click', (e) => {
    if (!elements.emojiPicker.contains(e.target) && e.target !== elements.emojiBtn) {
        elements.emojiPicker.classList.remove('active');
    }
});

// Reaction picker
document.querySelectorAll('.reaction-picker span').forEach(emoji => {
    emoji.addEventListener('click', (e) => {
        e.stopPropagation();
        const msgId = parseInt(elements.reactionPicker.dataset.messageId);
        socket.emit('add_reaction', {
            message_id: msgId,
            emoji: emoji.dataset.emoji
        });
        closeReactionPicker();
    });
});

// Scroll button
elements.chatArea.addEventListener('scroll', () => {
    const { scrollTop, scrollHeight, clientHeight } = elements.chatArea;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 200;
    elements.scrollBottomBtn.classList.toggle('visible', !isNearBottom);
});

elements.scrollBottomBtn.addEventListener('click', () => scrollToBottom());

// Search
elements.searchBtn.addEventListener('click', () => {
    elements.searchBar.classList.toggle('active');
    if (elements.searchBar.classList.contains('active')) {
        elements.searchInput.focus();
    } else {
        elements.searchResults.classList.remove('active');
    }
});

elements.closeSearch.addEventListener('click', () => {
    elements.searchBar.classList.remove('active');
    elements.searchResults.classList.remove('active');
    elements.searchInput.value = '';
});

let searchTimeout;
elements.searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    const query = elements.searchInput.value.trim();
    
    if (query.length < 2) {
        elements.searchResults.classList.remove('active');
        return;
    }
    
    searchTimeout = setTimeout(() => {
        socket.emit('search_messages', {
            conversation_id: state.currentConversationId,
            query: query
        });
    }, 300);
});

// Mobile menu
elements.menuToggle.addEventListener('click', () => {
    elements.sidebar.classList.toggle('open');
});

// New chat
elements.newChatBtn.addEventListener('click', () => {
    const name = prompt('Tên cuộc trò chuyện mới:');
    if (name && name.trim()) {
        socket.emit('create_conversation', { name: name.trim() });
    }
});

// Theme toggle
elements.themeToggle.addEventListener('click', () => {
    const newTheme = document.body.classList.contains('dark-theme') ? 'light' : 'dark';
    applyTheme(newTheme);
    socket.emit('update_setting', { key: 'theme', value: newTheme });
});

// Sound toggle
elements.soundToggle.addEventListener('click', () => {
    const newSound = !state.soundEnabled;
    applySoundSetting(newSound);
    socket.emit('update_setting', { key: 'sound_enabled', value: newSound.toString() });
});

// Settings modal
elements.settingsBtn.addEventListener('click', () => {
    elements.settingsModal.classList.add('active');
});

elements.closeSettings.addEventListener('click', () => {
    elements.settingsModal.classList.remove('active');
});

elements.moodSlider.addEventListener('input', () => {
    elements.moodValue.textContent = elements.moodSlider.value;
});

elements.saveSettings.addEventListener('click', () => {
    socket.emit('update_conversation', {
        conversation_id: state.currentConversationId,
        name: elements.convNameInput.value.trim(),
        ai_name: elements.aiNameInput.value.trim(),
        user_name: elements.userNameInput.value.trim(),
        mood: parseInt(elements.moodSlider.value)
    });
    elements.settingsModal.classList.remove('active');
});

elements.deleteConvBtn.addEventListener('click', () => {
    if (confirm('Xoá cuộc trò chuyện này? Không thể hoàn tác!')) {
        socket.emit('delete_conversation', {
            conversation_id: state.currentConversationId
        });
        elements.settingsModal.classList.remove('active');
    }
});

// Export modal
elements.exportBtn.addEventListener('click', () => {
    elements.exportModal.classList.add('active');
});

elements.closeExport.addEventListener('click', () => {
    elements.exportModal.classList.remove('active');
});

elements.exportTxt.addEventListener('click', () => {
    window.location.href = `/export/${state.currentConversationId}/txt`;
    elements.exportModal.classList.remove('active');
});

elements.exportJson.addEventListener('click', () => {
    window.location.href = `/export/${state.currentConversationId}/json`;
    elements.exportModal.classList.remove('active');
});

// Close modals on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.classList.remove('active');
        }
    });
});

// Close sidebar on outside click (mobile)
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 900 && 
        elements.sidebar.classList.contains('open') &&
        !elements.sidebar.contains(e.target) &&
        e.target !== elements.menuToggle) {
        closeSidebar();
    }
});

// ========== INIT ==========
elements.messageInput.focus();
console.log('🌸 Minh Thy Chat v2.0 initialized');