// API Base URLs
const API_LIVE_STATS = '/api/live_stats';
const API_STATUSES = '/api/statuses';
const API_PERSONALITIES = '/api/personalities';
const API_LEVEL_CONFIGS = '/api/level_configs';
const API_CUSTOM_COMMANDS = '/api/custom_commands';
const API_CHAT_CONFIGS = '/api/chat_configs';

// --- Background Canvas Animation ---
function initAnimation() {
    const canvas = document.getElementById('bg-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    let particles = [];

    class Particle {
        constructor() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 2;
            this.speedX = Math.random() * 0.5 - 0.25;
            this.speedY = Math.random() * 0.5 - 0.25;
            this.color = `rgba(0, 240, 255, ${Math.random() * 0.5 + 0.1})`;
        }
        update() {
            this.x += this.speedX;
            this.y += this.speedY;

            if (this.x > canvas.width) this.x = 0;
            if (this.x < 0) this.x = canvas.width;
            if (this.y > canvas.height) this.y = 0;
            if (this.y < 0) this.y = canvas.height;
        }
        draw() {
            ctx.fillStyle = this.color;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    function init() {
        particles = [];
        for (let i = 0; i < 100; i++) {
            particles.push(new Particle());
        }
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        for (let i = 0; i < particles.length; i++) {
            particles[i].update();
            particles[i].draw();
        }
        requestAnimationFrame(animate);
    }

    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        init();
    });

    init();
    animate();
}

// --- Live Stats Manager (Overview) ---

function formatUptime(seconds) {
    const d = Math.floor(seconds / (3600*24));
    const h = Math.floor(seconds % (3600*24) / 3600);
    const m = Math.floor(seconds % 3600 / 60);
    return `${d}d ${h}h ${m}m`;
}

function updateElementText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}
function updateElementHTML(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
}

function updateAuraGauge(percent) {
    const dashOffset = 440 - (440 * percent) / 100;
    const circle = document.getElementById('aura-circle');
    const text = document.getElementById('aura-text');
    if (circle) circle.style.strokeDashoffset = dashOffset;
    if (text) text.textContent = `${Math.round(percent)}%`;
}

async function fetchLiveStats() {
    // Only attempt if we are on a page that needs it, or at least check if one element exists
    if (!document.getElementById('stat-ram') && !document.getElementById('aura-text')) return;

    try {
        const res = await fetch(API_LIVE_STATS);
        if (!res.ok) throw new Error('Failed to fetch live stats');
        const data = await res.json();

        // Overview Page
        updateElementText('stat-commands', (data.ai_api.ai_chat_counter || 0).toLocaleString());
        updateElementText('stat-servers', data.discord.total_server_count);
        updateElementText('stat-ping', `${data.discord.ping_ms}ms`);
        updateElementText('stat-db-status', data.database.latency_ms > 0 ? "Connected" : "Disconnected");

        updateElementText('stat-ram', `${data.hardware.ram_usage_mb} MB`);
        updateElementText('stat-uptime', formatUptime(data.discord.uptime_seconds));

        updateAuraGauge(data.hardware.cpu_usage_percent);

    } catch (err) {
        console.error("Live Stats Error:", err);
    }
}

// --- Status Manager (Modules) ---

async function fetchStatuses() {
    if (!document.getElementById('status-list')) return;

    try {
        const res = await fetch(API_STATUSES);
        if (!res.ok) throw new Error('Failed to fetch statuses');
        const statuses = await res.json();
        renderStatuses(statuses);
    } catch (err) {
        console.error(err);
        const list = document.getElementById('status-list');
        if (list) list.innerHTML = `<div class="text-error text-sm text-center">Error loading statuses.</div>`;
    }
}

function renderStatuses(statuses) {
    const list = document.getElementById('status-list');
    if(!list) return;
    list.innerHTML = '';

    if (statuses.length === 0) {
        list.innerHTML = `<div class="text-center text-on-surface-variant italic text-sm">No statuses found.</div>`;
        return;
    }

    statuses.forEach(status => {
        const div = document.createElement('div');
        div.className = "bg-surface-container-high p-4 rounded-xl flex justify-between items-center border border-[#353535]";

        const activeDot = status.active
            ? '<span class="w-2 h-2 rounded-full bg-[#00FF94] mr-3 shadow-[0_0_8px_#00FF94]"></span>'
            : '<span class="w-2 h-2 rounded-full bg-[#888888] mr-3"></span>';

        const textDiv = document.createElement('div');
        textDiv.className = "flex-1 overflow-hidden";
        textDiv.innerHTML = `
            <div class="flex items-center mb-1">
                ${activeDot}
                <span class="text-[10px] uppercase font-bold text-outline tracking-wider">${status.type}</span>
            </div>
            <div class="text-white truncate font-medium text-sm" title="${status.text}">${status.text}</div>
        `;

        const btn = document.createElement('button');
        btn.className = "ml-4 text-[#888888] hover:text-error transition-colors focus:outline-none focus:ring-2 focus:ring-[#EBB2FF] rounded";
        btn.title = "Delete";
        btn.setAttribute("aria-label", `Delete status ${status.text}`);
        btn.innerHTML = `<span class="material-symbols-outlined text-lg" data-icon="delete">delete</span>`;
        btn.onclick = () => deleteStatus(status.text);

        div.appendChild(textDiv);
        div.appendChild(btn);
        list.appendChild(div);
    });
}

const statusForm = document.getElementById('status-form');
if (statusForm) {
    statusForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const type = document.getElementById('status-type').value;
        const text = document.getElementById('status-text').value;
        const active = document.getElementById('status-active').checked;

        try {
            const res = await fetch(API_STATUSES, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type, text, active })
            });
            if (res.ok) {
                const textInput = document.getElementById('status-text');
                if (textInput) textInput.value = '';
                fetchStatuses();
            } else {
                alert("Failed to save status.");
            }
        } catch (err) {
            console.error(err);
        }
    });
}

async function deleteStatus(text) {
    if (!confirm(`Delete status "${text}"?`)) return;
    try {
        const res = await fetch(API_STATUSES, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        if (res.ok) fetchStatuses();
    } catch (err) {
        console.error(err);
    }
}

// --- Personality Manager (Modules) ---

async function fetchPersonalities() {
    if (!document.getElementById('personality-list')) return;

    try {
        const res = await fetch(API_PERSONALITIES);
        if (!res.ok) throw new Error('Failed to fetch personalities');
        const personalities = await res.json();
        renderPersonalities(personalities);
    } catch (err) {
        console.error(err);
        const list = document.getElementById('personality-list');
        if (list) list.innerHTML = `<div class="text-error text-sm text-center">Error loading personalities.</div>`;
    }
}

function renderPersonalities(personalities) {
    const list = document.getElementById('personality-list');
    if(!list) return;
    list.innerHTML = '';

    if (personalities.length === 0) {
        list.innerHTML = `<div class="text-center text-on-surface-variant italic text-sm">No personalities found.</div>`;
        return;
    }

    personalities.forEach(p => {
        const div = document.createElement('div');
        div.className = "bg-surface-container-high p-4 rounded-xl border border-[#353535] flex flex-col group hover:border-primary/30 transition-colors";

        const headerDiv = document.createElement('div');
        headerDiv.className = "flex justify-between items-start mb-3";

        const nameSpan = document.createElement('span');
        nameSpan.className = "font-bold text-primary font-headline";
        nameSpan.textContent = p.name;

        const btnContainer = document.createElement('div');
        btnContainer.className = "flex space-x-3";

        const editBtn = document.createElement('button');
        editBtn.className = "text-[#888888] hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-[#EBB2FF] rounded";
        editBtn.title = "Edit";
        editBtn.setAttribute("aria-label", `Edit personality ${p.name}`);
        editBtn.innerHTML = `<span class="material-symbols-outlined text-sm" data-icon="edit">edit</span>`;
        editBtn.onclick = () => editPersonality(p.name, p.prompt);

        const delBtn = document.createElement('button');
        delBtn.className = "text-[#888888] hover:text-error transition-colors focus:outline-none focus:ring-2 focus:ring-[#EBB2FF] rounded";
        delBtn.title = "Delete";
        delBtn.setAttribute("aria-label", `Delete personality ${p.name}`);
        delBtn.innerHTML = `<span class="material-symbols-outlined text-sm" data-icon="delete">delete</span>`;
        delBtn.onclick = () => deletePersonality(p.name);

        btnContainer.appendChild(editBtn);
        btnContainer.appendChild(delBtn);
        headerDiv.appendChild(nameSpan);
        headerDiv.appendChild(btnContainer);

        const promptDiv = document.createElement('div');
        promptDiv.className = "text-xs text-on-surface-variant font-body line-clamp-3 leading-relaxed";
        promptDiv.title = p.prompt;
        promptDiv.textContent = p.prompt;

        div.appendChild(headerDiv);
        div.appendChild(promptDiv);

        list.appendChild(div);
    });
}

const personalityForm = document.getElementById('personality-form');
if (personalityForm) {
    personalityForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('personality-name').value;
        const prompt = document.getElementById('personality-prompt').value;

        try {
            const res = await fetch(API_PERSONALITIES, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, prompt })
            });
            if (res.ok) {
                const nameInput = document.getElementById('personality-name');
                const promptInput = document.getElementById('personality-prompt');
                if (nameInput) nameInput.value = '';
                if (promptInput) promptInput.value = '';
                fetchPersonalities();
            } else {
                const data = await res.json();
                alert(data.error || "Failed to save personality.");
            }
        } catch (err) {
            console.error(err);
        }
    });
}

async function deletePersonality(name) {
    if (!confirm(`Delete personality "${name}"?`)) return;
    try {
        const res = await fetch(API_PERSONALITIES, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        if (res.ok) fetchPersonalities();
    } catch (err) {
        console.error(err);
    }
}

function editPersonality(name, prompt) {
    const nameInput = document.getElementById('personality-name');
    const promptInput = document.getElementById('personality-prompt');
    if (nameInput) nameInput.value = name;
    if (promptInput) promptInput.value = prompt;
    window.scrollTo({ top: 0, behavior: 'smooth' });
}


// --- Global Server Selector & Configuration Loaders ---

async function fetchUserGuilds() {
    try {
        const res = await fetch('/api/user_guilds');
        if (res.ok) {
            const guilds = await res.json();
            const globalSelect = document.getElementById('global-server-selector');
            if(!globalSelect) return;

            globalSelect.innerHTML = '<option value="">-- Select a Server --</option>';

            guilds.forEach(g => {
                const opt = document.createElement('option');
                opt.value = g.id;
                opt.textContent = g.name;
                globalSelect.appendChild(opt);
            });

            // Restore selection
            const savedGuildId = localStorage.getItem('silk_selected_guild_id');
            if (savedGuildId && guilds.some(g => g.id === savedGuildId)) {
                globalSelect.value = savedGuildId;
                triggerServerConfigLoad(savedGuildId);
            }
        }
    } catch (err) {
        console.error("Failed to load user guilds:", err);
    }
}

const globalSelector = document.getElementById('global-server-selector');
if (globalSelector) {
    globalSelector.addEventListener('change', (e) => {
        const guildId = e.target.value;
        if (guildId) {
            localStorage.setItem('silk_selected_guild_id', guildId);
            triggerServerConfigLoad(guildId);
        } else {
            localStorage.removeItem('silk_selected_guild_id');
            clearServerConfigs();
        }
    });
}

function triggerServerConfigLoad(guildId) {
    loadLevelingConfig(guildId);
    loadCustomCommands(guildId);
    loadChatConfig(guildId);
}

function clearServerConfigs() {
    // Leveling
    if(document.getElementById('level-min-xp')) document.getElementById('level-min-xp').value = '';
    // Custom Commands
    if(document.getElementById('cc-list')) document.getElementById('cc-list').innerHTML = '<div class="text-center text-on-surface-variant italic text-sm col-span-full">Select a server to view custom commands.</div>';
    // Chat Config
    if(document.getElementById('chat-enabled')) document.getElementById('chat-enabled').checked = false;
}


// --- Leveling Manager (Settings) ---

async function loadLevelingConfig(guildId) {
    if (!document.getElementById('leveling-form')) return;

    try {
        const res = await fetch(`${API_LEVEL_CONFIGS}/${guildId}`);
        if (res.ok) {
            const config = await res.json();
            const minXp = document.getElementById('level-min-xp');
            const maxXp = document.getElementById('level-max-xp');
            const cooldown = document.getElementById('level-text-cooldown');
            const vcMin = document.getElementById('level-vc-xp-min');
            const vcEnabled = document.getElementById('level-vc-enabled');
            if (minXp) minXp.value = config.text_min_xp ?? 15;
            if (maxXp) maxXp.value = config.text_max_xp ?? 25;
            if (cooldown) cooldown.value = config.text_cooldown ?? 60;
            if (vcMin) vcMin.value = config.vc_xp_per_minute ?? 5;
            if (vcEnabled) vcEnabled.checked = config.vc_xp_enabled ?? true;
        }
    } catch (err) {
        console.error("Failed to load leveling config:", err);
    }
}

const levelingForm = document.getElementById('leveling-form');
if (levelingForm) {
    levelingForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const guildId = document.getElementById('global-server-selector').value;
        if (!guildId) {
            alert("Please select a server first from the top navbar.");
            return;
        }

        const payload = {
            text_min_xp: parseInt(document.getElementById('level-min-xp').value),
            text_max_xp: parseInt(document.getElementById('level-max-xp').value),
            text_cooldown: parseInt(document.getElementById('level-text-cooldown').value),
            vc_xp_per_minute: parseInt(document.getElementById('level-vc-xp-min').value),
            vc_xp_enabled: document.getElementById('level-vc-enabled').checked
        };

        try {
            const res = await fetch(`${API_LEVEL_CONFIGS}/${guildId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                alert("Leveling configuration saved successfully.");
            } else {
                alert("Failed to save configuration.");
            }
        } catch (err) {
            console.error(err);
            alert("An error occurred.");
        }
    });
}

// --- Custom Commands Manager (Settings) ---

async function loadCustomCommands(guildId) {
    if (!document.getElementById('cc-list')) return;

    try {
        const res = await fetch(`${API_CUSTOM_COMMANDS}/${guildId}`);
        if (!res.ok) throw new Error('Failed to fetch custom commands');
        const commands = await res.json();
        renderCustomCommands(commands);
    } catch (err) {
        console.error(err);
        const list = document.getElementById('cc-list');
        if (list) list.innerHTML = `<div class="text-error text-sm text-center col-span-full">Error loading custom commands.</div>`;
    }
}

function renderCustomCommands(commands) {
    const list = document.getElementById('cc-list');
    if(!list) return;
    list.innerHTML = '';

    if (commands.length === 0) {
        list.innerHTML = `<div class="text-center text-on-surface-variant italic text-sm col-span-full">No custom commands found.</div>`;
        return;
    }

    commands.forEach(c => {
        const div = document.createElement('div');
        div.className = "bg-surface-container-high p-4 rounded-xl border border-[#353535] flex flex-col";

        const headerDiv = document.createElement('div');
        headerDiv.className = "flex justify-between items-start mb-2";

        const triggerSpan = document.createElement('span');
        triggerSpan.className = "font-bold text-primary font-mono";
        triggerSpan.textContent = c.trigger;

        const btnContainer = document.createElement('div');
        btnContainer.className = "flex space-x-2";

        const editBtn = document.createElement('button');
        editBtn.className = "text-[#888888] hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-[#EBB2FF] rounded";
        editBtn.title = "Edit";
        editBtn.setAttribute("aria-label", `Edit custom command ${c.trigger}`);
        editBtn.innerHTML = `<span class="material-symbols-outlined text-sm" data-icon="edit">edit</span>`;
        editBtn.onclick = () => {
            const triggerInput = document.getElementById('cc-trigger');
            const responseInput = document.getElementById('cc-response');
            const replyCheckbox = document.getElementById('cc-reply-directly');
            if (triggerInput) {
                triggerInput.value = c.trigger;
                triggerInput.focus();
            }
            if (responseInput) responseInput.value = c.response;
            if (replyCheckbox) replyCheckbox.checked = c.reply_directly || false;
        };

        const delBtn = document.createElement('button');
        delBtn.className = "text-[#888888] hover:text-error transition-colors focus:outline-none focus:ring-2 focus:ring-[#EBB2FF] rounded";
        delBtn.title = "Delete";
        delBtn.setAttribute("aria-label", `Delete custom command ${c.trigger}`);
        delBtn.innerHTML = `<span class="material-symbols-outlined text-sm" data-icon="delete">delete</span>`;
        delBtn.onclick = () => deleteCustomCommand(c.trigger);

        btnContainer.appendChild(editBtn);
        btnContainer.appendChild(delBtn);
        headerDiv.appendChild(triggerSpan);
        headerDiv.appendChild(btnContainer);

        const replyDiv = document.createElement('div');
        replyDiv.className = "text-[10px] text-outline font-mono mb-2 tracking-widest uppercase";
        replyDiv.textContent = `Reply Directly: ${c.reply_directly ? 'YES' : 'NO'}`;

        const responseDiv = document.createElement('div');
        responseDiv.className = "text-sm text-on-surface-variant line-clamp-2";
        responseDiv.title = c.response;
        responseDiv.textContent = c.response;

        div.appendChild(headerDiv);
        div.appendChild(replyDiv);
        div.appendChild(responseDiv);

        list.appendChild(div);
    });
}

const ccForm = document.getElementById('cc-form');
if (ccForm) {
    ccForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const guildId = document.getElementById('global-server-selector').value;
        if (!guildId) {
            alert("Please select a server first from the top navbar.");
            return;
        }

        const trigger = document.getElementById('cc-trigger').value;
        const response = document.getElementById('cc-response').value;
        const reply_directly = document.getElementById('cc-reply-directly').checked;

        try {
            const res = await fetch(`${API_CUSTOM_COMMANDS}/${guildId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ trigger, response, reply_directly })
            });
            if (res.ok) {
                const triggerInput = document.getElementById('cc-trigger');
                const responseInput = document.getElementById('cc-response');
                const replyCheckbox = document.getElementById('cc-reply-directly');
                if (triggerInput) triggerInput.value = '';
                if (responseInput) responseInput.value = '';
                if (replyCheckbox) replyCheckbox.checked = false;
                loadCustomCommands(guildId);
            } else {
                alert("Failed to save custom command.");
            }
        } catch (err) {
            console.error(err);
        }
    });
}

async function deleteCustomCommand(trigger) {
    const guildId = document.getElementById('global-server-selector').value;
    if (!guildId) return;

    if (!confirm(`Delete custom command for trigger "${trigger}"?`)) return;
    try {
        const res = await fetch(`${API_CUSTOM_COMMANDS}/${guildId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trigger })
        });
        if (res.ok) loadCustomCommands(guildId);
    } catch (err) {
        console.error(err);
    }
}

// --- Auto-Chat Config Manager (Modules) ---

async function loadChatConfig(guildId) {
    if (!document.getElementById('chat-config-form')) return;

    try {
        const res = await fetch(`${API_CHAT_CONFIGS}/${guildId}`);
        if (res.ok) {
            const config = await res.json();
            const enabled = document.getElementById('chat-enabled');
            const lang = document.getElementById('chat-language');
            if (enabled) enabled.checked = config.enabled || false;
            if (lang) lang.value = config.language || "English";
        }
    } catch (err) {
        console.error("Failed to load chat config:", err);
    }
}

const chatConfigForm = document.getElementById('chat-config-form');
if (chatConfigForm) {
    chatConfigForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const guildId = document.getElementById('global-server-selector').value;
        if (!guildId) {
            alert("Please select a server first from the top navbar.");
            return;
        }

        const payload = {
            enabled: document.getElementById('chat-enabled').checked,
            language: document.getElementById('chat-language').value
        };

        try {
            const res = await fetch(`${API_CHAT_CONFIGS}/${guildId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                alert("Auto-Chat configuration saved successfully.");
            } else {
                alert("Failed to save Auto-Chat configuration.");
            }
        } catch (err) {
            console.error(err);
            alert("An error occurred.");
        }
    });
}

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    initAnimation();

    fetchLiveStats();
    if (document.getElementById('stat-ram') || document.getElementById('aura-text')) {
        setInterval(fetchLiveStats, 60000); // Poll every 60 seconds on overview
    }

    fetchStatuses();
    fetchPersonalities();
    fetchUserGuilds();
});
