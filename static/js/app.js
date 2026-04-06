let ws = null;
let currentCampaignId = 1; // Set via your auth flow

export function initWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/ws/map/${currentCampaignId}`);
    
    ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        
        if (payload.type === 'chat') {
            const log = document.getElementById('chat-log');
            
            // FIX: Prevent crashes when typing indicator doesn't exist
            const typingEl = document.getElementById('typing'); 
            if (typingEl && payload.role === 'ai') typingEl.remove();
            
            // FIX: XSS Protection via textContent
            const safeMsg = document.createElement('div');
            safeMsg.textContent = payload.message;
            
            log.innerHTML += `<div class="msg-${payload.role}"><b>${payload.sender}:</b> ${safeMsg.innerHTML}</div>`; 
            log.scrollTop = log.scrollHeight;
        }
    };
}

export async function sendChat() {
    const input = document.getElementById('chat-input');
    const msg = input.value;
    if (!msg) return;
    input.value = '';

    const log = document.getElementById('chat-log');
    log.innerHTML += `<div id="typing" class="msg-ai" style="opacity: 0.5;"><i>DM is resolving action...</i></div>`; 
    log.scrollTop = log.scrollHeight;

    try { 
        const res = await fetch('/api/chat', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({ campaign_id: currentCampaignId, message: msg, character_name: "Player" }) 
        });
        const data = await res.json();
        if (data.error) {
            const typingEl = document.getElementById('typing');
            if (typingEl) typingEl.remove(); // Safely remove
            log.innerHTML += `<div class="msg-ai" style="color: #e74c3c;"><b>System:</b> ${data.error}</div>`; 
        }
    } catch(e) { console.error("Chat Error:", e); }
}

// FIX: Added the missing AI outline generator
window.generateStoryOutline = async function() {
    try {
        const res = await fetch(`/api/campaigns/${currentCampaignId}/generate-outline`, { method: 'POST' });
        if (res.ok) alert("Story outline generated successfully!");
        else alert("Failed to generate outline.");
    } catch(e) { console.error(e); }
};

// Make sendChat available globally for the HTML inline handlers
window.sendChat = sendChat;
