/**
 * MIDI Deck Web Interface JavaScript
 *
 * Provides all frontend functionality for the MIDI Deck web interface.
 */

// =============================================================================
// Global State
// =============================================================================

let currentSession = null;
let audioStatus = null;

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Show a status message to the user
 */
function showMessage(message, type = 'info') {
    const messageEl = document.getElementById('status-message');
    if (!messageEl) return;

    messageEl.textContent = message;
    messageEl.className = `message ${type}`;
    messageEl.style.display = 'block';

    // Auto-hide after 5 seconds
    setTimeout(() => {
        messageEl.style.display = 'none';
    }, 5000);
}

/**
 * Hide status message
 */
function hideMessage() {
    const messageEl = document.getElementById('status-message');
    if (messageEl) {
        messageEl.style.display = 'none';
    }
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleString();
}

/**
 * Format volume as percentage
 */
function formatVolume(volume) {
    return Math.round(volume * 100) + '%';
}

/**
 * Show a modal dialog
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
    }
}

/**
 * Close a modal dialog
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Generic API call wrapper
 */
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(`/api${endpoint}`, options);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Request failed');
        }

        return result;
    } catch (error) {
        console.error(`API call failed: ${endpoint}`, error);
        throw error;
    }
}

// =============================================================================
// Dashboard Functions
// =============================================================================

/**
 * Refresh dashboard with current status
 */
async function refreshDashboard() {
    try {
        // Load current session
        const sessions = await apiCall('/sessions');
        const current = sessions.find(s => s.is_current);

        if (current) {
            currentSession = current;
            document.getElementById('session-name').textContent = current.name;
            document.getElementById('session-updated').textContent =
                'Last updated: ' + formatDate(current.updated_at);
        }

        // Load audio status
        audioStatus = await apiCall('/status');

        // Update system status counts
        document.getElementById('sinks-count').textContent = audioStatus.sinks.length;
        document.getElementById('outputs-count').textContent = audioStatus.outputs.length;
        document.getElementById('connections-count').textContent =
            audioStatus.connections.filter(c => c.connected).length;

        // Update channels overview
        const channelsEl = document.getElementById('channels-overview');
        if (channelsEl) {
            channelsEl.innerHTML = audioStatus.sinks.map(sink => `
                <div class="channel-card">
                    <h4>${sink.name} (Channel ${sink.channel})</h4>
                    <div class="volume-display">${formatVolume(sink.volume)}</div>
                    <div>
                        ${sink.muted ? '<span class="status-badge muted">Muted</span>' :
                                      '<span class="status-badge active">Active</span>'}
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Failed to refresh dashboard:', error);
    }
}

/**
 * Save current session
 */
async function saveCurrentSession() {
    if (!currentSession) {
        showMessage('No session to save', 'error');
        return;
    }

    try {
        await apiCall(`/sessions/${currentSession.id}/save`, 'POST');
        showMessage('Session saved successfully', 'success');
        refreshDashboard();
    } catch (error) {
        showMessage('Failed to save session: ' + error.message, 'error');
    }
}

// =============================================================================
// Configuration Functions
// =============================================================================

/**
 * Load hardware outputs list
 */
async function loadHardwareOutputs() {
    try {
        const outputs = await apiCall('/hardware-outputs');
        const listEl = document.getElementById('hardware-outputs-list');

        if (!listEl) return;

        listEl.innerHTML = outputs.map(output => `
            <div class="config-item">
                <div class="config-item-info">
                    <h4>${output.name}</h4>
                    <p>${output.device_name}</p>
                    <p class="text-muted">${output.description || ''}</p>
                </div>
                <div class="config-item-actions">
                    <button onclick="deleteHardwareOutput(${output.id})" class="btn btn-danger btn-small">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load hardware outputs:', error);
    }
}

/**
 * Load virtual sinks list
 */
async function loadVirtualSinks() {
    try {
        const sinks = await apiCall('/virtual-sinks');
        const listEl = document.getElementById('virtual-sinks-list');

        if (!listEl) return;

        sinks.sort((a, b) => a.channel_number - b.channel_number);

        listEl.innerHTML = sinks.map(sink => `
            <div class="config-item">
                <div class="config-item-info">
                    <h4>Channel ${sink.channel_number}: ${sink.name}</h4>
                    <p class="text-muted">${sink.description || ''}</p>
                </div>
                <div class="config-item-actions">
                    <button onclick="deleteVirtualSink(${sink.id})" class="btn btn-danger btn-small">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load virtual sinks:', error);
    }
}

/**
 * Load general settings
 */
async function loadSettings() {
    try {
        const config = await apiCall('/config');

        config.forEach(item => {
            const input = document.getElementById(item.key);
            if (input) {
                input.value = item.value;
            }
        });
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

/**
 * Save general settings
 */
async function saveSettings(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const config = {};

    for (const [key, value] of formData.entries()) {
        config[key] = value;
    }

    try {
        await apiCall('/config', 'POST', { config });
        showMessage('Settings saved successfully', 'success');
    } catch (error) {
        showMessage('Failed to save settings: ' + error.message, 'error');
    }
}

/**
 * Show add output modal
 */
function showAddOutputModal() {
    showModal('add-output-modal');
}

/**
 * Add hardware output
 */
async function addOutput(event) {
    event.preventDefault();

    const form = event.target;
    const data = {
        name: document.getElementById('output-name').value,
        device_name: document.getElementById('output-device').value,
        description: document.getElementById('output-description').value
    };

    try {
        await apiCall('/hardware-outputs', 'POST', data);
        showMessage('Hardware output added successfully', 'success');
        closeModal('add-output-modal');
        form.reset();
        loadHardwareOutputs();
    } catch (error) {
        showMessage('Failed to add output: ' + error.message, 'error');
    }
}

/**
 * Delete hardware output
 */
async function deleteHardwareOutput(id) {
    if (!confirm('Are you sure you want to delete this hardware output?')) {
        return;
    }

    try {
        await apiCall(`/hardware-outputs/${id}`, 'DELETE');
        showMessage('Hardware output deleted', 'success');
        loadHardwareOutputs();
    } catch (error) {
        showMessage('Failed to delete output: ' + error.message, 'error');
    }
}

/**
 * Show add sink modal
 */
function showAddSinkModal() {
    showModal('add-sink-modal');
}

/**
 * Add virtual sink
 */
async function addSink(event) {
    event.preventDefault();

    const form = event.target;
    const data = {
        channel_number: parseInt(document.getElementById('sink-channel').value),
        name: document.getElementById('sink-name').value,
        description: document.getElementById('sink-description').value
    };

    try {
        await apiCall('/virtual-sinks', 'POST', data);
        showMessage('Virtual sink added successfully', 'success');
        closeModal('add-sink-modal');
        form.reset();
        loadVirtualSinks();
    } catch (error) {
        showMessage('Failed to add sink: ' + error.message, 'error');
    }
}

/**
 * Delete virtual sink
 */
async function deleteVirtualSink(id) {
    if (!confirm('Are you sure you want to delete this virtual sink?')) {
        return;
    }

    try {
        await apiCall(`/virtual-sinks/${id}`, 'DELETE');
        showMessage('Virtual sink deleted', 'success');
        loadVirtualSinks();
    } catch (error) {
        showMessage('Failed to delete sink: ' + error.message, 'error');
    }
}

/**
 * Discover hardware devices
 */
async function discoverHardware() {
    try {
        const result = await apiCall('/hardware/discover');
        const devicesEl = document.getElementById('discovered-devices');

        if (!devicesEl) return;

        devicesEl.style.display = 'block';
        devicesEl.innerHTML = result.devices.map(device => `
            <div class="discovered-device">
                <div class="discovered-device-info">
                    <strong>${device.description || device.name}</strong>
                    <code>${device.name}</code>
                </div>
                <button onclick="useDevice('${device.name}')" class="btn btn-primary btn-small">Use</button>
            </div>
        `).join('');

        showMessage(`Found ${result.devices.length} devices`, 'success');
    } catch (error) {
        showMessage('Failed to discover devices: ' + error.message, 'error');
    }
}

/**
 * Use discovered device
 */
function useDevice(deviceName) {
    document.getElementById('output-device').value = deviceName;
    showAddOutputModal();
}

// =============================================================================
// Session Management Functions
// =============================================================================

/**
 * Load sessions list
 */
async function loadSessions() {
    try {
        const sessions = await apiCall('/sessions');
        const listEl = document.getElementById('sessions-list');

        if (!listEl) return;

        if (sessions.length === 0) {
            listEl.innerHTML = '<p class="text-center text-muted">No sessions found. Create one to get started.</p>';
            return;
        }

        listEl.innerHTML = sessions.map(session => `
            <div class="session-card ${session.is_current ? 'current' : ''}">
                <h4>
                    ${session.name}
                    ${session.is_current ? '<span class="current-badge">CURRENT</span>' : ''}
                </h4>
                <p>${session.description || 'No description'}</p>
                <div class="session-meta">
                    <div>Created: ${formatDate(session.created_at)}</div>
                    <div>Updated: ${formatDate(session.updated_at)}</div>
                </div>
                <div class="session-actions">
                    ${!session.is_current ?
                        `<button onclick="activateSession(${session.id})" class="btn btn-primary btn-small">Load</button>` :
                        ''}
                    <button onclick="saveSession(${session.id})" class="btn btn-success btn-small">Save</button>
                    <button onclick="showEditSessionModal(${session.id})" class="btn btn-secondary btn-small">Edit</button>
                    ${!session.is_current ?
                        `<button onclick="deleteSession(${session.id})" class="btn btn-danger btn-small">Delete</button>` :
                        ''}
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load sessions:', error);
    }
}

/**
 * Show create session modal
 */
function showCreateSessionModal() {
    showModal('create-session-modal');
}

/**
 * Create new session
 */
async function createSession(event) {
    event.preventDefault();

    const form = event.target;
    const data = {
        name: document.getElementById('session-name').value,
        description: document.getElementById('session-description').value
    };

    try {
        const result = await apiCall('/sessions', 'POST', data);

        // Optionally save current state to new session
        if (document.getElementById('save-current-state').checked) {
            await apiCall(`/sessions/${result.id}/save`, 'POST');
        }

        showMessage('Session created successfully', 'success');
        closeModal('create-session-modal');
        form.reset();
        loadSessions();
    } catch (error) {
        showMessage('Failed to create session: ' + error.message, 'error');
    }
}

/**
 * Show edit session modal
 */
async function showEditSessionModal(id) {
    try {
        const session = await apiCall(`/sessions/${id}`);

        document.getElementById('edit-session-id').value = session.id;
        document.getElementById('edit-session-name').value = session.name;
        document.getElementById('edit-session-description').value = session.description || '';

        showModal('edit-session-modal');
    } catch (error) {
        showMessage('Failed to load session: ' + error.message, 'error');
    }
}

/**
 * Update session
 */
async function updateSession(event) {
    event.preventDefault();

    const id = document.getElementById('edit-session-id').value;
    const data = {
        name: document.getElementById('edit-session-name').value,
        description: document.getElementById('edit-session-description').value
    };

    try {
        await apiCall(`/sessions/${id}`, 'PUT', data);
        showMessage('Session updated successfully', 'success');
        closeModal('edit-session-modal');
        loadSessions();
    } catch (error) {
        showMessage('Failed to update session: ' + error.message, 'error');
    }
}

/**
 * Activate (load) a session
 */
async function activateSession(id) {
    try {
        await apiCall(`/sessions/${id}/activate`, 'POST');
        showMessage('Session loaded successfully', 'success');
        loadSessions();
    } catch (error) {
        showMessage('Failed to load session: ' + error.message, 'error');
    }
}

/**
 * Save a session
 */
async function saveSession(id) {
    try {
        await apiCall(`/sessions/${id}/save`, 'POST');
        showMessage('Session saved successfully', 'success');
        loadSessions();
    } catch (error) {
        showMessage('Failed to save session: ' + error.message, 'error');
    }
}

/**
 * Delete a session
 */
async function deleteSession(id) {
    if (!confirm('Are you sure you want to delete this session?')) {
        return;
    }

    try {
        await apiCall(`/sessions/${id}`, 'DELETE');
        showMessage('Session deleted', 'success');
        loadSessions();
    } catch (error) {
        showMessage('Failed to delete session: ' + error.message, 'error');
    }
}

// =============================================================================
// Control Page Functions
// =============================================================================

/**
 * Load control page status
 */
async function loadControlStatus() {
    try {
        audioStatus = await apiCall('/status');

        // Update channel controls
        const channelsEl = document.getElementById('channels-control');
        if (channelsEl) {
            channelsEl.innerHTML = audioStatus.sinks.map(sink => `
                <div class="channel-control">
                    <h4>${sink.name} (Ch ${sink.channel})</h4>

                    <div class="volume-control">
                        <div class="volume-label">
                            <span>Volume</span>
                            <span id="volume-value-${sink.id}">${formatVolume(sink.volume)}</span>
                        </div>
                        <input type="range"
                               class="volume-slider"
                               id="volume-${sink.id}"
                               min="0"
                               max="100"
                               value="${Math.round(sink.volume * 100)}"
                               oninput="updateVolumeDisplay(${sink.id}, this.value)"
                               onchange="setVolume(${sink.id}, this.value / 100)">
                    </div>

                    <div class="mute-control">
                        <button onclick="toggleMute(${sink.id})"
                                class="btn ${sink.muted ? 'btn-danger' : 'btn-secondary'}">
                            ${sink.muted ? 'Unmute' : 'Mute'}
                        </button>
                    </div>
                </div>
            `).join('');
        }

        // Update routing matrix
        const matrixEl = document.getElementById('routing-matrix');
        if (matrixEl) {
            matrixEl.innerHTML = `
                <table class="routing-table">
                    <thead>
                        <tr>
                            <th>Sink / Output</th>
                            ${audioStatus.outputs.map(output => `<th>${output.name}</th>`).join('')}
                            <th>Mute</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${audioStatus.sinks.map(sink => `
                            <tr>
                                <td><strong>${sink.name}</strong></td>
                                ${audioStatus.outputs.map(output => {
                                    const conn = audioStatus.connections.find(
                                        c => c.sink_id === sink.id && c.output_id === output.id
                                    );
                                    const connected = conn && conn.connected;
                                    return `
                                        <td>
                                            <button onclick="toggleConnection(${sink.id}, ${output.id})"
                                                    class="connection-toggle ${connected ? 'connected' : ''}">
                                                ${connected ? '✓' : ''}
                                            </button>
                                        </td>
                                    `;
                                }).join('')}
                                <td>
                                    <button onclick="toggleMute(${sink.id})"
                                            class="connection-toggle ${sink.muted ? 'muted' : ''}">
                                        ${sink.muted ? '✗' : ''}
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
    } catch (error) {
        console.error('Failed to load control status:', error);
    }
}

/**
 * Update volume display while sliding
 */
function updateVolumeDisplay(sinkId, value) {
    const displayEl = document.getElementById(`volume-value-${sinkId}`);
    if (displayEl) {
        displayEl.textContent = value + '%';
    }
}

/**
 * Set volume for a sink
 */
async function setVolume(sinkId, volume) {
    try {
        await apiCall(`/sinks/${sinkId}/volume`, 'POST', { volume });
    } catch (error) {
        showMessage('Failed to set volume: ' + error.message, 'error');
    }
}

/**
 * Toggle mute for a sink
 */
async function toggleMute(sinkId) {
    try {
        const sink = audioStatus.sinks.find(s => s.id === sinkId);
        if (!sink) return;

        await apiCall(`/sinks/${sinkId}/mute`, 'POST', { muted: !sink.muted });
        loadControlStatus();
    } catch (error) {
        showMessage('Failed to toggle mute: ' + error.message, 'error');
    }
}

/**
 * Toggle connection between sink and output
 */
async function toggleConnection(sinkId, outputId) {
    try {
        await apiCall(`/connections/${sinkId}/${outputId}`, 'POST');
        loadControlStatus();
    } catch (error) {
        showMessage('Failed to toggle connection: ' + error.message, 'error');
    }
}

// =============================================================================
// MIDI Mappings Functions
// =============================================================================

/**
 * Load MIDI mappings
 */
async function loadMidiMappings() {
    try {
        const mappings = await apiCall('/midi-mappings');
        const sinks = await apiCall('/virtual-sinks');

        // Group mappings by sink
        const groupedMappings = {};
        sinks.forEach(sink => {
            groupedMappings[sink.id] = {
                sink: sink,
                mappings: mappings.filter(m => m.sink_id === sink.id)
            };
        });

        const listEl = document.getElementById('midi-mappings-list');
        if (!listEl) return;

        listEl.innerHTML = Object.values(groupedMappings).map(group => `
            <div class="midi-channel-group">
                <h4>${group.sink.name} (Channel ${group.sink.channel_number})</h4>
                ${group.mappings.map(mapping => `
                    <div class="midi-mapping">
                        <div class="midi-mapping-info">
                            <strong>Note ${mapping.midi_note}: ${mapping.action.toUpperCase()}</strong>
                            <span>${mapping.description || ''}</span>
                        </div>
                        <button onclick="showEditMappingModal(${mapping.id})"
                                class="btn btn-secondary btn-small">Edit</button>
                    </div>
                `).join('')}
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load MIDI mappings:', error);
    }
}

/**
 * Load MIDI configuration
 */
async function loadMidiConfig() {
    try {
        const config = await apiCall('/config');

        const midiDevice = config.find(c => c.key === 'midi_device_name');
        const jitterThreshold = config.find(c => c.key === 'jitter_threshold');

        if (midiDevice) {
            const el = document.getElementById('midi-device-name');
            if (el) el.textContent = midiDevice.value;
        }

        if (jitterThreshold) {
            const el = document.getElementById('jitter-threshold');
            if (el) el.textContent = jitterThreshold.value;
        }
    } catch (error) {
        console.error('Failed to load MIDI config:', error);
    }
}

/**
 * Show edit MIDI mapping modal
 */
async function showEditMappingModal(id) {
    try {
        const mapping = await apiCall(`/midi-mappings/${id}`);
        const sinks = await apiCall('/virtual-sinks');

        document.getElementById('mapping-id').value = mapping.id;
        document.getElementById('mapping-note').value = mapping.midi_note;
        document.getElementById('mapping-action').value = mapping.action;
        document.getElementById('mapping-description').value = mapping.description || '';

        // Populate sink dropdown
        const sinkSelect = document.getElementById('mapping-sink');
        sinkSelect.innerHTML = sinks.map(sink => `
            <option value="${sink.id}" ${sink.id === mapping.sink_id ? 'selected' : ''}>
                ${sink.name} (Channel ${sink.channel_number})
            </option>
        `).join('');

        showModal('edit-mapping-modal');
    } catch (error) {
        showMessage('Failed to load mapping: ' + error.message, 'error');
    }
}

/**
 * Update MIDI mapping
 */
async function updateMidiMapping(event) {
    event.preventDefault();

    const id = document.getElementById('mapping-id').value;
    const data = {
        sink_id: parseInt(document.getElementById('mapping-sink').value),
        action: document.getElementById('mapping-action').value,
        description: document.getElementById('mapping-description').value
    };

    try {
        await apiCall(`/midi-mappings/${id}`, 'PUT', data);
        showMessage('MIDI mapping updated successfully', 'success');
        closeModal('edit-mapping-modal');
        loadMidiMappings();
    } catch (error) {
        showMessage('Failed to update mapping: ' + error.message, 'error');
    }
}

// =============================================================================
// Initialize
// =============================================================================

console.log('MIDI Deck Web Interface loaded');

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
};
