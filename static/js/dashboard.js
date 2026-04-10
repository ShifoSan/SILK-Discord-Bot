        function toggleAllAccordions() {
            const panels = document.querySelectorAll('details.accordion-panel');
            const btn = document.getElementById('toggle-all-btn');
            const allOpen = Array.from(panels).every(p => p.hasAttribute('open'));

            panels.forEach(p => {
                if (allOpen) {
                    p.removeAttribute('open');
                } else {
                    p.setAttribute('open', '');
                }
            });

            btn.textContent = allOpen ? 'Expand All' : 'Collapse All';
        }
        // API Base URLs
        const API_LIVE_STATS = '/api/live_stats';
        const API_STATUSES = '/api/statuses';
        const API_PERSONALITIES = '/api/personalities';

        // --- Live Stats Manager ---

        function formatUptime(seconds) {
            const d = Math.floor(seconds / (3600*24));
            const h = Math.floor(seconds % (3600*24) / 3600);
            const m = Math.floor(seconds % 3600 / 60);
            return `${d}d ${h}h ${m}m`;
        }

        function setStatusColor(elementId, status) {
            const el = document.getElementById(elementId);
            if (!el) return;
            el.textContent = status;
            if (status === "Connected") {
                el.className = "font-mono text-discord-success font-bold";
            } else {
                el.className = "font-mono text-discord-danger font-bold";
            }
        }

        async function fetchLiveStats() {
            try {
                const res = await fetch(API_LIVE_STATS);
                if (!res.ok) throw new Error('Failed to fetch live stats');
                const data = await res.json();

                // Hardware
                document.getElementById('stat-ram').textContent = `${data.hardware.ram_usage_mb} MB`;
                document.getElementById('stat-cpu').textContent = `${data.hardware.cpu_usage_percent} %`;

                // Discord
                document.getElementById('stat-ping').textContent = `${data.discord.ping_ms} ms`;
                document.getElementById('stat-uptime').textContent = formatUptime(data.discord.uptime_seconds);
                document.getElementById('stat-servers').textContent = data.discord.total_server_count;
                document.getElementById('stat-members').textContent = data.discord.total_member_count;
                document.getElementById('stat-server-names').innerHTML = data.discord.connected_server_names.join('<br>');

                // AI/API
                document.getElementById('stat-chats').textContent = data.ai_api.ai_chat_counter;
                document.getElementById('stat-voice').textContent = data.ai_api.active_voice_channels;
                setStatusColor('stat-gemini', data.ai_api.api_connection_status.gemini);
                setStatusColor('stat-hf', data.ai_api.api_connection_status.huggingface);

                // Database
                document.getElementById('stat-db-ping').textContent = `${data.database.latency_ms} ms`;
                document.getElementById('stat-db-users').textContent = data.database.total_leveling_users;
                document.getElementById('stat-persona').textContent = data.database.active_global_persona;

            } catch (err) {
                console.error("Live Stats Error:", err);
            }
        }

        // --- Status Manager ---

        async function fetchStatuses() {
            try {
                const res = await fetch(API_STATUSES);
                if (!res.ok) throw new Error('Failed to fetch statuses');
                const statuses = await res.json();
                renderStatuses(statuses);
            } catch (err) {
                console.error(err);
                document.getElementById('status-list').innerHTML = `<div class="text-discord-danger text-sm text-center">Error loading statuses.</div>`;
            }
        }

        function renderStatuses(statuses) {
            const list = document.getElementById('status-list');
            list.innerHTML = '';

            if (statuses.length === 0) {
                list.innerHTML = `<div class="text-center text-gray-500 italic text-sm">No statuses found.</div>`;
                return;
            }

            statuses.forEach(status => {
                const div = document.createElement('div');
                div.className = "bg-discord-darkest p-3 rounded flex justify-between items-center border border-gray-700";

                const activeDot = status.active
                    ? '<span class="w-2 h-2 rounded-full bg-discord-success mr-2 inline-block" title="Active"></span>'
                    : '<span class="w-2 h-2 rounded-full bg-gray-500 mr-2 inline-block" title="Inactive"></span>';

                const textDiv = document.createElement('div');
                textDiv.className = "flex-1 overflow-hidden";
                textDiv.innerHTML = `
                    <div class="flex items-center">
                        ${activeDot}
                        <span class="text-xs uppercase font-bold text-gray-400 mr-2">${status.type}</span>
                    </div>
                `;

                const titleSpan = document.createElement('div');
                titleSpan.className = "text-white truncate font-medium mt-1";
                titleSpan.textContent = status.text;
                titleSpan.title = status.text;
                textDiv.appendChild(titleSpan);

                const btn = document.createElement('button');
                btn.className = "ml-3 text-gray-400 hover:text-discord-danger transition-colors";
                btn.title = "Delete";
                btn.innerHTML = `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>`;
                btn.onclick = () => deleteStatus(status.text);

                div.appendChild(textDiv);
                div.appendChild(btn);
                list.appendChild(div);
            });
        }
        document.getElementById('status-form').addEventListener('submit', async (e) => {
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
                    document.getElementById('status-text').value = '';
                    fetchStatuses();
                } else {
                    alert("Failed to save status.");
                }
            } catch (err) {
                console.error(err);
            }
        });

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

        // --- Personality Manager ---

        async function fetchPersonalities() {
            try {
                const res = await fetch(API_PERSONALITIES);
                if (!res.ok) throw new Error('Failed to fetch personalities');
                const personalities = await res.json();
                renderPersonalities(personalities);
            } catch (err) {
                console.error(err);
                document.getElementById('personality-list').innerHTML = `<div class="text-discord-danger text-sm text-center">Error loading personalities.</div>`;
            }
        }

        function renderPersonalities(personalities) {
            const list = document.getElementById('personality-list');
            list.innerHTML = '';

            if (personalities.length === 0) {
                list.innerHTML = `<div class="text-center text-gray-500 italic text-sm">No personalities found.</div>`;
                return;
            }

            personalities.forEach(p => {
                const div = document.createElement('div');
                div.className = "bg-discord-darkest p-3 rounded border border-gray-700 flex flex-col";

                const headerDiv = document.createElement('div');
                headerDiv.className = "flex justify-between items-start mb-2";

                const nameSpan = document.createElement('span');
                nameSpan.className = "font-bold text-discord-blurple";
                nameSpan.textContent = p.name;

                const btnContainer = document.createElement('div');
                btnContainer.className = "flex space-x-2";

                const editBtn = document.createElement('button');
                editBtn.className = "text-gray-400 hover:text-white transition-colors";
                editBtn.title = "Edit";
                editBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>`;
                editBtn.onclick = () => editPersonality(p.name, p.prompt);

                const delBtn = document.createElement('button');
                delBtn.className = "text-gray-400 hover:text-discord-danger transition-colors";
                delBtn.title = "Delete";
                delBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>`;
                delBtn.onclick = () => deletePersonality(p.name);

                btnContainer.appendChild(editBtn);
                btnContainer.appendChild(delBtn);
                headerDiv.appendChild(nameSpan);
                headerDiv.appendChild(btnContainer);

                const promptDiv = document.createElement('div');
                promptDiv.className = "text-xs text-gray-400 font-mono line-clamp-2";
                promptDiv.title = p.prompt;
                promptDiv.textContent = p.prompt;

                div.appendChild(headerDiv);
                div.appendChild(promptDiv);

                list.appendChild(div);
            });
        }
        document.getElementById('personality-form').addEventListener('submit', async (e) => {
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
                    document.getElementById('personality-name').value = '';
                    document.getElementById('personality-prompt').value = '';
                    fetchPersonalities();
                } else {
                    alert("Failed to save personality.");
                }
            } catch (err) {
                console.error(err);
            }
        });

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
            document.getElementById('personality-name').value = name;
            document.getElementById('personality-prompt').value = prompt;
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }


        // --- Leveling Manager ---
        const API_LEVEL_CONFIGS = '/api/level_configs';

        document.getElementById('level-server-id').addEventListener('change', async (e) => {
            const guildId = e.target.value;
            if (!guildId) return;

            try {
                const res = await fetch(`${API_LEVEL_CONFIGS}/${guildId}`);
                if (res.ok) {
                    const config = await res.json();
                    document.getElementById('level-min-xp').value = config.text_min_xp ?? 15;
                    document.getElementById('level-max-xp').value = config.text_max_xp ?? 25;
                    document.getElementById('level-text-cooldown').value = config.text_cooldown ?? 60;
                    document.getElementById('level-vc-xp-min').value = config.vc_xp_per_minute ?? 5;
                    document.getElementById('level-vc-enabled').checked = config.vc_xp_enabled ?? true;
                }
            } catch (err) {
                console.error("Failed to load leveling config:", err);
            }
        });

        document.getElementById('leveling-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const guildId = document.getElementById('level-server-id').value;
            if (!guildId) {
                alert("Please select a server first.");
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
                    alert("Configuration saved successfully.");
                } else {
                    alert("Failed to save configuration.");
                }
            } catch (err) {
                console.error(err);
                alert("An error occurred.");
            }
        });

        // --- Custom Commands Manager ---
        const API_CUSTOM_COMMANDS = '/api/custom_commands';

        document.getElementById('cc-server-id').addEventListener('change', async (e) => {
            const guildId = e.target.value;
            if (!guildId) {
                document.getElementById('cc-list').innerHTML = '<div class="text-center text-gray-500 italic text-sm col-span-full">Select a server to view custom commands.</div>';
                return;
            }
            fetchCustomCommands(guildId);
        });

        async function fetchCustomCommands(guildId) {
            try {
                const res = await fetch(`${API_CUSTOM_COMMANDS}/${guildId}`);
                if (!res.ok) throw new Error('Failed to fetch custom commands');
                const commands = await res.json();
                renderCustomCommands(commands);
            } catch (err) {
                console.error(err);
                document.getElementById('cc-list').innerHTML = `<div class="text-discord-danger text-sm text-center col-span-full">Error loading custom commands.</div>`;
            }
        }

        function renderCustomCommands(commands) {
            const list = document.getElementById('cc-list');
            list.innerHTML = '';

            if (commands.length === 0) {
                list.innerHTML = `<div class="text-center text-gray-500 italic text-sm col-span-full">No custom commands found.</div>`;
                return;
            }

            commands.forEach(c => {
                const div = document.createElement('div');
                div.className = "bg-discord-darkest p-3 rounded border border-gray-700 flex flex-col";

                const headerDiv = document.createElement('div');
                headerDiv.className = "flex justify-between items-start mb-2";

                const triggerSpan = document.createElement('span');
                triggerSpan.className = "font-bold text-discord-blurple";
                triggerSpan.textContent = c.trigger;

                const btnContainer = document.createElement('div');
                btnContainer.className = "flex space-x-2";

                const editBtn = document.createElement('button');
                editBtn.className = "text-gray-400 hover:text-white transition-colors";
                editBtn.title = "Edit";
                editBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>`;
                editBtn.onclick = () => {
                    document.getElementById('cc-trigger').value = c.trigger;
                    document.getElementById('cc-response').value = c.response;
                    document.getElementById('cc-reply-directly').checked = c.reply_directly || false;
                };

                const delBtn = document.createElement('button');
                delBtn.className = "text-gray-400 hover:text-discord-danger transition-colors";
                delBtn.title = "Delete";
                delBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>`;
                delBtn.onclick = () => deleteCustomCommand(c.trigger);

                btnContainer.appendChild(editBtn);
                btnContainer.appendChild(delBtn);
                headerDiv.appendChild(triggerSpan);
                headerDiv.appendChild(btnContainer);

                const replyDiv = document.createElement('div');
                replyDiv.className = "text-xs text-gray-400 mb-1";
                replyDiv.textContent = `Reply Directly: ${c.reply_directly ? 'Yes' : 'No'}`;

                const responseDiv = document.createElement('div');
                responseDiv.className = "text-sm text-gray-300 line-clamp-2";
                responseDiv.title = c.response;
                responseDiv.textContent = c.response;

                div.appendChild(headerDiv);
                div.appendChild(replyDiv);
                div.appendChild(responseDiv);

                list.appendChild(div);
            });
        }

        document.getElementById('cc-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const guildId = document.getElementById('cc-server-id').value;
            if (!guildId) {
                alert("Please select a server first.");
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
                    document.getElementById('cc-trigger').value = '';
                    document.getElementById('cc-response').value = '';
                    document.getElementById('cc-reply-directly').checked = false;
                    fetchCustomCommands(guildId);
                } else {
                    alert("Failed to save custom command.");
                }
            } catch (err) {
                console.error(err);
            }
        });

        async function deleteCustomCommand(trigger) {
            const guildId = document.getElementById('cc-server-id').value;
            if (!guildId) return;

            if (!confirm(`Delete custom command for trigger "${trigger}"?`)) return;
            try {
                const res = await fetch(`${API_CUSTOM_COMMANDS}/${guildId}`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ trigger })
                });
                if (res.ok) fetchCustomCommands(guildId);
            } catch (err) {
                console.error(err);
            }
        }


        async function fetchUserGuilds() {
            try {
                const res = await fetch('/api/user_guilds');
                if (res.ok) {
                    const guilds = await res.json();
                    const selectLevel = document.getElementById('level-server-id');
                    const selectCc = document.getElementById('cc-server-id');

                    selectLevel.innerHTML = '<option value="">-- Select a Server --</option>';
                    selectCc.innerHTML = '<option value="">-- Select a Server --</option>';

                    guilds.forEach(g => {
                        const optLevel = document.createElement('option');
                        optLevel.value = g.id;
                        optLevel.textContent = g.name;
                        selectLevel.appendChild(optLevel);

                        const optCc = document.createElement('option');
                        optCc.value = g.id;
                        optCc.textContent = g.name;
                        selectCc.appendChild(optCc);
                    });
                } else {
                    document.getElementById('level-server-id').innerHTML = '<option value="">Error loading servers</option>';
                    document.getElementById('cc-server-id').innerHTML = '<option value="">Error loading servers</option>';
                }
            } catch (err) {
                console.error("Failed to load user guilds:", err);
            }
        }

        function initAnimation() {
            // Animation logic goes here
        }

        // --- Init ---
        document.addEventListener('DOMContentLoaded', () => {
            initAnimation();

            fetchLiveStats();
            setInterval(fetchLiveStats, 60000); // Poll every 60 seconds

            fetchStatuses();
            fetchPersonalities();
            fetchUserGuilds();
        });
