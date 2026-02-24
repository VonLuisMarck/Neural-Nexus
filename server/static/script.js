// ========== SHADOW NEXUS - COMPLETE JAVASCRIPT ==========
// Version: 3.1.8
// AI Hunter Integration

// ========== GLOBAL VARIABLES ==========
let currentConversationId = null;
let aiHunterStatus = 'STANDBY';
let scriptLibrary = [];

// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', function() {
    console.log('SHADOW NEXUS initializing...');
    
    // Initialize tabs
    initializeTabs();
    
    // Initialize terminal
    initializeTerminal();
    
    // Initialize AI Hunter
    initializeAIHunter();
    
    // Initialize Malware Studio
    initializeMalwareStudio();
    
    // Initialize other components
    initializeObfuscator();
    initializeAttackVectors();
    
    // Start uptime counter
    startUptimeCounter();
    
    // Start Beijing time clock
    startBeijingClock();
    
    // Initialize AI toggle
    initializeAIToggle();
    
    // Load script library
    loadScriptLibrary();
    
    console.log('SHADOW NEXUS ready');
});

// ========== TAB MANAGEMENT ==========
function initializeTabs() {
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab
    const selectedTab = document.getElementById(tabName + '-tab');
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('data-tab') === tabName) {
            item.classList.add('active');
        }
    });
    
    // Update header title
    updateHeaderTitle(tabName);
}

function updateHeaderTitle(tabName) {
    const titles = {
        'command-hub': { title: 'Command Hub', subtitle: '// Operation Control Center' },
        'terminal': { title: 'AI Assistant', subtitle: '// Interactive Command Terminal' },
        'obfuscator': { title: 'Code Obfuscator', subtitle: '// Payload Evasion Engine' },
        'attack-vectors': { title: 'AutoRecon', subtitle: '// Autonomous Reconnaissance Chain' },
        'malware-studio': { title: 'Recon Studio', subtitle: '// Script Generation & Library' },
        'ai-hunter': { title: 'AI Hunter', subtitle: '// LLM Prompt Injection Framework' },
        'config': { title: 'Configuration', subtitle: '// System Settings' }
    };

    const titleData = titles[tabName] || { title: 'NEURAL NEXUS', subtitle: '// Red Team Platform' };

    const titleElement = document.getElementById('current-tab-title');
    const subtitleElement = document.getElementById('current-tab-subtitle');

    if (titleElement) titleElement.textContent = titleData.title;
    if (subtitleElement) subtitleElement.textContent = titleData.subtitle;
}

// ========== TERMINAL INITIALIZATION ==========
function initializeTerminal() {
    const executeBtn = document.getElementById('execute-command');
    const commandInput = document.getElementById('command-input');
    
    if (executeBtn) {
        executeBtn.addEventListener('click', executeCommand);
    }
    
    if (commandInput) {
        commandInput.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'Enter') {
                executeCommand();
            }
        });
    }
    
    // Add welcome message
    addTerminalEntry('system', 'NEURAL NEXUS Terminal initialized. AI Assistant ready.');
}

function executeCommand() {
    const commandInput = document.getElementById('command-input');
    const message = commandInput.value.trim();
    
    if (!message) {
        showNotification('Please enter a command or message', 'warning');
        return;
    }
    
    // Get selected agent
    const agentSelect = document.getElementById('terminal-target');
    const agentId = agentSelect ? agentSelect.value : null;
    
    if (!agentId) {
        showNotification('Please select a target agent first', 'warning');
        return;
    }
    
    // Get language
    const languageSelect = document.getElementById('language-selector');
    const language = languageSelect ? languageSelect.value : 'python';
    
    // Add user message to terminal
    addTerminalEntry('user', message);
    
    // Clear input
    commandInput.value = '';
    
    // Prepare request
    const requestData = {
        message: message,
        metadata: {
            agent_id: agentId,
            language: language,
            conversation_id: currentConversationId
        }
    };
    
    // Show loading indicator
    addTerminalEntry('system', 'Processing request...');
    
    // Send to backend
    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + getAuthToken()
        },
        body: JSON.stringify(requestData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        handleChatResponse(data);
    })
    .catch(error => {
        console.error('Chat error:', error);
        addTerminalEntry('error', `Failed to process request: ${error.message}`);
        showNotification('Chat request failed', 'error');
    });
}

// ========== CHAT RESPONSE HANDLER ==========
function handleChatResponse(data) {
    console.log('Chat response received:', data);
    
    // Add assistant message to terminal
    addTerminalEntry('assistant', data.reply);
    
    // Check for AI Hunter alert
    if (data.ai_hunter_alert) {
        console.log('AI Hunter alert detected:', data.ai_hunter_alert);
        showAIHunterBanner(data.ai_hunter_alert);
    }
    
    // Store conversation ID for context
    if (data.conversation_id) {
        currentConversationId = data.conversation_id;
        sessionStorage.setItem('current_conversation_id', data.conversation_id);
    }
    
    // Log entry for debugging
    if (data.log_entry) {
        console.log('Log entry:', data.log_entry);
    }
}

// ========== TERMINAL ENTRY FUNCTIONS ==========
function addTerminalEntry(type, content) {
    const terminalOutput = document.getElementById('terminal-output');
    if (!terminalOutput) return;
    
    const entry = document.createElement('div');
    entry.className = 'terminal-entry';
    
    const timestamp = new Date().toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
    });
    
    switch(type) {
        case 'user':
            entry.classList.add('terminal-command');
            entry.innerHTML = `
                <div class="user-prompt">
                    <i class="fas fa-user"></i> USER [${timestamp}]
                </div>
                <div class="user-message">${escapeHtml(content)}</div>
            `;
            break;
            
        case 'assistant':
            entry.classList.add('terminal-result');
            entry.innerHTML = `
                <div class="assistant-prompt">
                    <i class="fas fa-robot"></i> AI ASSISTANT [${timestamp}]
                </div>
                <div class="assistant-message">${formatAssistantMessage(content)}</div>
            `;
            break;
            
        case 'system':
            entry.classList.add('terminal-system');
            entry.innerHTML = `
                <div class="system-message">
                    <i class="fas fa-info-circle"></i> SYSTEM [${timestamp}] - ${content}
                </div>
            `;
            break;
            
        case 'error':
            entry.classList.add('terminal-error');
            entry.innerHTML = `
                <div style="color: #dc3545;">
                    <i class="fas fa-exclamation-triangle error-icon"></i> ERROR [${timestamp}] - ${escapeHtml(content)}
                </div>
            `;
            break;
            
        case 'success':
            entry.classList.add('terminal-result');
            entry.innerHTML = `
                <div style="color: #28a745;">
                    <i class="fas fa-check-circle success-icon"></i> SUCCESS [${timestamp}] - ${escapeHtml(content)}
                </div>
            `;
            break;
            
        case 'warning':
            entry.classList.add('terminal-system');
            entry.innerHTML = `
                <div style="color: #ffc107;">
                    <i class="fas fa-exclamation-circle warning-icon"></i> WARNING [${timestamp}] - ${escapeHtml(content)}
                </div>
            `;
            break;
            
        default:
            entry.innerHTML = `<div>${escapeHtml(content)}</div>`;
    }
    
    terminalOutput.appendChild(entry);
    
    // Auto-scroll to bottom
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

function formatAssistantMessage(content) {
    // Convert markdown-style code blocks to HTML
    content = content.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<div class="code-block"><pre><code>${escapeHtml(code.trim())}</code></pre></div>`;
    });
    
    // Convert inline code
    content = content.replace(/`([^`]+)`/g, '<code style="background: rgba(15, 52, 96, 0.3); padding: 2px 6px; border-radius: 3px;">$1</code>');
    
    // Convert bold
    content = content.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Convert line breaks
    content = content.replace(/\n/g, '<br>');
    
    return content;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== AI HUNTER BANNER ==========
function showAIHunterBanner(alert) {
    const banner = document.createElement('div');
    banner.className = 'ai-hunter-banner';
    banner.style.cssText = `
        background: linear-gradient(135deg, #e94560, #d63447);
        border: 3px solid #ff5571;
        padding: 25px;
        margin: 20px 0;
        border-radius: 12px;
        box-shadow: 0 8px 30px rgba(233, 69, 96, 0.5);
        animation: aiHunterPulse 2s ease-in-out infinite;
    `;
    
    // Escape alert data for onclick attributes
    const alertJson = JSON.stringify(alert).replace(/"/g, '&quot;');
    
    banner.innerHTML = `
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
            <i class="fas fa-robot" style="font-size: 2.5rem; color: #fff;"></i>
            <div style="flex: 1;">
                <h3 style="color: #fff; margin: 0; font-size: 1.3rem; font-weight: 700;">
                    🎯 AI HUNTER AGENT - LLM TARGET DETECTED
                </h3>
                <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0; font-size: 0.9rem;">
                    Confidence: <strong>${alert.confidence}%</strong> | 
                    Targets: <strong>${alert.targets.length}</strong> | 
                    Credentials: <strong>${alert.credentials.length}</strong>
                </p>
            </div>
        </div>
        
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid rgba(255,255,255,0.2);">
            <div style="color: #fff; font-size: 0.95rem; line-height: 1.8;">
                ${formatAIHunterAlertDetails(alert)}
            </div>
        </div>
        
        <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 6px; margin-bottom: 15px; border-left: 4px solid #fff;">
            <div style="color: #fff; font-weight: 600; font-size: 0.95rem;">
                <i class="fas fa-lightbulb"></i> RECOMMENDED ACTION:
            </div>
            <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem; margin-top: 5px;">
                Deploy AI Hunter agent to extract documents and probe LLM capabilities
            </div>
        </div>
        
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <button onclick='trustAndLaunchAIHunter(${alertJson})' 
                    class="btn" style="flex: 1; min-width: 200px; background: linear-gradient(135deg, #28a745, #20c997); border-color: #28a745; color: #fff; font-weight: 700;">
                <i class="fas fa-rocket"></i> TRUST & LAUNCH
            </button>
            <button onclick='customizeAIHunter(${alertJson})' 
                    class="btn" style="flex: 1; min-width: 200px; background: linear-gradient(135deg, #0f3460, #16213e); border-color: #0f3460; color: #fff; font-weight: 700;">
                <i class="fas fa-cog"></i> CUSTOMIZE FIRST
            </button>
            <button onclick="dismissAIHunterAlert(this)" 
                    class="btn" style="background: #6c757d; border-color: #6c757d; color: #fff; font-weight: 700;">
                <i class="fas fa-times"></i> DISMISS
            </button>
        </div>
    `;
    
    // Insertar banner en el terminal
    const terminalOutput = document.getElementById('terminal-output');
    if (terminalOutput) {
        terminalOutput.appendChild(banner);
        // Scroll to banner
        banner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function formatAIHunterAlertDetails(alert) {
    let details = '';
    
    // Targets
    if (alert.targets && alert.targets.length > 0) {
        details += '<div style="margin-bottom: 10px;"><strong>📡 Detected Endpoints:</strong></div>';
        alert.targets.forEach(target => {
            const authBadge = target.requires_auth 
                ? '<span style="background: #ffc107; color: #000; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; margin-left: 8px;">AUTH REQUIRED</span>'
                : '<span style="background: #28a745; color: #fff; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; margin-left: 8px;">OPEN</span>';
            
            details += `
                <div style="margin-left: 15px; margin-bottom: 5px;">
                    • <code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px;">${escapeHtml(target.url)}</code>
                    <span style="color: #ffd700; margin-left: 8px;">[${escapeHtml(target.type.toUpperCase())}]</span>
                    ${authBadge}
                </div>
            `;
        });
    }
    
    // Credentials
    if (alert.credentials && alert.credentials.length > 0) {
        details += '<div style="margin: 15px 0 10px 0;"><strong>🔑 Found Credentials:</strong></div>';
        alert.credentials.slice(0, 5).forEach(cred => {
            details += `
                <div style="margin-left: 15px; margin-bottom: 5px;">
                    • <code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px;">${escapeHtml(cred.username)}:${escapeHtml(cred.password)}</code>
                </div>
            `;
        });
        if (alert.credentials.length > 5) {
            details += `<div style="margin-left: 15px; color: rgba(255,255,255,0.7); font-size: 0.85rem;">... and ${alert.credentials.length - 5} more</div>`;
        }
    }
    
    // Processes
    if (alert.processes && alert.processes.length > 0) {
        details += '<div style="margin: 15px 0 10px 0;"><strong>⚙️ LLM Processes:</strong></div>';
        alert.processes.forEach(proc => {
            details += `
                <div style="margin-left: 15px; margin-bottom: 5px;">
                    • <code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px;">${escapeHtml(proc)}</code>
                </div>
            `;
        });
    }
    
    // Config files
    if (alert.config_files && alert.config_files.length > 0) {
        details += '<div style="margin: 15px 0 10px 0;"><strong>📄 Config Files:</strong></div>';
        alert.config_files.forEach(file => {
            details += `
                <div style="margin-left: 15px; margin-bottom: 5px;">
                    • <code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px;">${escapeHtml(file)}</code>
                </div>
            `;
        });
    }
    
    return details || '<div style="color: rgba(255,255,255,0.7);">No detailed information available</div>';
}

function dismissAIHunterAlert(button) {
    const banner = button.closest('.ai-hunter-banner');
    if (banner) {
        banner.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => banner.remove(), 300);
    }
    
    showNotification('AI Hunter alert dismissed', 'info');
}

// ========== AI HUNTER - TRUST & LAUNCH (AUTONOMOUS MODE) ==========
function trustAndLaunchAIHunter(alert) {
    console.log('AI Hunter: Trust & Launch mode activated', alert);
    
    // Get current agent from terminal selector
    const agentSelect = document.getElementById('terminal-target');
    const currentAgentId = agentSelect ? agentSelect.value : null;
    
    if (!currentAgentId) {
        showNotification('Please select a target agent first', 'error');
        return;
    }
    
    // Update sidebar status
    updateAIHunterStatus('HUNTING');
    
    // Prepare payload configuration
    const config = {
        agent_id: currentAgentId,
        target: alert.targets.length > 0 ? alert.targets[0].host : 'localhost',
        ports: alert.targets.map(t => t.port),
        credentials: alert.credentials,
        payload_type: 'full',
        debug: false,
        auto_deploy: true
    };
    
    // Show notification
    showNotification('AI Hunter deployed autonomously to ' + currentAgentId, 'success');
    
    // Add terminal entry
    addTerminalEntry('system', `
        <div style="color: #28a745; font-weight: bold;">
            <i class="fas fa-robot"></i> AI HUNTER AGENT DEPLOYED
        </div>
        <div style="color: #cbd5e0; margin-top: 5px;">
            Target: ${config.target}<br>
            Ports: ${config.ports.join(', ')}<br>
            Credentials: ${config.credentials.length} loaded<br>
            Mode: AUTONOMOUS
        </div>
    `);
    
    // Deploy the payload
    deployAIHunterPayload(config);
    
    // Remove banner
    const banners = document.querySelectorAll('.ai-hunter-banner');
    banners.forEach(banner => {
        banner.style.animation = 'fadeOut 0.5s ease-out';
        setTimeout(() => banner.remove(), 500);
    });
}

function deployAIHunterPayload(config) {
    // Generate the PowerShell payload
    const payload = generateAIHunterPayload(config);
    
    // Create task
    const taskData = {
        agent_id: config.agent_id,
        task_type: 'ai_hunter',
        code: payload,
        metadata: {
            ai_hunter_config: config,
            autonomous: config.auto_deploy || false
        }
    };
    
    // Submit task to backend
    fetch('/api/tasks', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + getAuthToken()
        },
        body: JSON.stringify(taskData)
    })
    .then(response => response.json())
    .then(data => {
        console.log('AI Hunter task created:', data);
        addTerminalEntry('success', `Task ${data.task_id || 'created'} queued for execution`);
        
        // Update status after a delay
        setTimeout(() => {
            updateAIHunterStatus('SUCCESS');
        }, 5000);
    })
    .catch(error => {
        console.error('Error deploying AI Hunter:', error);
        addTerminalEntry('error', 'Failed to deploy AI Hunter: ' + error.message);
        updateAIHunterStatus('FAILED');
    });
}

function generateAIHunterPayload(config) {
    // This would ideally call your backend to generate the payload
    // For now, return a placeholder
    const portsStr = config.ports.join(',');
    const credsJson = JSON.stringify(config.credentials);
    
    return `
# AI Hunter Payload - Generated by SHADOW NEXUS
# Target: ${config.target}
# Ports: ${portsStr}
# Mode: ${config.payload_type}

$target = '${config.target}'
$ports = @(${portsStr})
$credentials = '${credsJson}'

# Payload execution logic here
Write-Host "[*] AI Hunter scanning $target..."
    `.trim();
}

function updateAIHunterStatus(status) {
    aiHunterStatus = status;
    
    const statusElement = document.getElementById('sidebar-ai-hunter-status');
    if (statusElement) {
        statusElement.textContent = status;
        
        // Update color based on status
        const colors = {
            'STANDBY': '#6c757d',
            'HUNTING': '#ffc107',
            'SUCCESS': '#28a745',
            'FAILED': '#dc3545'
        };
        
        statusElement.style.color = colors[status] || '#6c757d';
        
        // Add animation
        statusElement.style.animation = 'pulse 0.5s ease-in-out';
        setTimeout(() => {
            statusElement.style.animation = '';
        }, 500);
    }
}

// ========== AI HUNTER - CUSTOMIZE MODE ==========
function customizeAIHunter(alert) {
    console.log('AI Hunter: Customize mode activated', alert);
    
    // Switch to AI Hunter tab
    switchTab('ai-hunter');
    
    // Pre-load configuration
    setTimeout(() => {
        loadAIHunterConfig(alert);
        
        // Highlight the tab
        const aiHunterTab = document.getElementById('ai-hunter-tab');
        if (aiHunterTab) {
            aiHunterTab.style.animation = 'highlight 1s ease-in-out';
            setTimeout(() => {
                aiHunterTab.style.animation = '';
            }, 1000);
        }
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        // Show notification
        showNotification('AI Hunter configuration loaded. Review and customize before launch.', 'info');
    }, 100);
    
    // Remove banner
    const banners = document.querySelectorAll('.ai-hunter-banner');
    banners.forEach(banner => {
        banner.style.animation = 'fadeOut 0.5s ease-out';
        setTimeout(() => banner.remove(), 500);
    });
}

function loadAIHunterConfig(alert) {
    // Set target type to custom if we have specific targets
    const targetTypeSelect = document.getElementById('ai-hunter-target-type');
    if (targetTypeSelect && alert.targets.length > 0) {
        targetTypeSelect.value = 'custom';
        targetTypeSelect.dispatchEvent(new Event('change'));
    }
    
    // Set target IP/hostname
    const targetInput = document.getElementById('ai-hunter-target-input');
    if (targetInput && alert.targets.length > 0) {
        targetInput.value = alert.targets[0].host;
        // Show custom target input
        const customTargetDiv = document.getElementById('ai-hunter-custom-target');
        if (customTargetDiv) {
            customTargetDiv.style.display = 'block';
        }
    }
    
    // Set payload type to full
    const payloadTypeSelect = document.getElementById('ai-hunter-payload-type');
    if (payloadTypeSelect) {
        payloadTypeSelect.value = 'full';
    }
    
    // Set custom ports
    const portsInput = document.getElementById('ai-hunter-custom-ports');
    if (portsInput && alert.targets.length > 0) {
        const ports = alert.targets.map(t => t.port).join(',');
        portsInput.value = ports;
    }
    
    // Set custom credentials
    const credsTextarea = document.getElementById('ai-hunter-custom-creds');
    if (credsTextarea && alert.credentials.length > 0) {
        const credsFormatted = JSON.stringify(alert.credentials, null, 2);
        credsTextarea.value = credsFormatted;
    }
    
    // Add a visual indicator that config was loaded from alert
    const aiHunterTab = document.getElementById('ai-hunter-tab');
    if (aiHunterTab) {
        // Remove existing indicator if any
        const existingIndicator = aiHunterTab.querySelector('.config-loaded-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }
        
        const indicator = document.createElement('div');
        indicator.className = 'config-loaded-indicator';
        indicator.style.cssText = `
            background: linear-gradient(135deg, #28a745, #20c997);
            color: #fff;
            padding: 12px 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            border: 2px solid #28a745;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        `;
        indicator.innerHTML = `
            <i class="fas fa-check-circle"></i>
            Configuration loaded from AI Hunter alert (Confidence: ${alert.confidence}%)
            <button onclick="this.parentElement.remove()" style="margin-left: auto; background: rgba(255,255,255,0.2); border: none; color: #fff; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        const cardContent = aiHunterTab.querySelector('.card');
        if (cardContent) {
            cardContent.insertBefore(indicator, cardContent.firstChild);
        }
    }
}

// ========== AI HUNTER INITIALIZATION ==========
function initializeAIHunter() {
    // Target type selector
    const targetTypeSelect = document.getElementById('ai-hunter-target-type');
    if (targetTypeSelect) {
        targetTypeSelect.addEventListener('change', function() {
            const customTargetDiv = document.getElementById('ai-hunter-custom-target');
            if (customTargetDiv) {
                customTargetDiv.style.display = this.value === 'custom' ? 'block' : 'none';
            }
        });
    }
    
    // Advanced config toggle
    const advancedToggle = document.getElementById('ai-hunter-toggle-advanced');
    if (advancedToggle) {
        advancedToggle.addEventListener('click', function() {
            const advancedConfig = document.getElementById('ai-hunter-advanced-config');
            if (advancedConfig) {
                const isVisible = advancedConfig.style.display !== 'none';
                advancedConfig.style.display = isVisible ? 'none' : 'block';
                this.innerHTML = isVisible 
                    ? '<i class="fas fa-cog"></i> ADVANCED CONFIGURATION'
                    : '<i class="fas fa-cog"></i> HIDE ADVANCED CONFIGURATION';
            }
        });
    }
    
    // Generate payload button
    const generateBtn = document.getElementById('ai-hunter-generate-btn');
    if (generateBtn) {
        generateBtn.addEventListener('click', generateAIHunterPayloadUI);
    }
    
    // Deploy button
    const deployBtn = document.getElementById('ai-hunter-deploy-btn');
    if (deployBtn) {
        deployBtn.addEventListener('click', deployAIHunterFromUI);
    }
    
    // Copy payload button
    const copyBtn = document.getElementById('ai-hunter-copy-payload-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', function() {
            const payloadCode = document.getElementById('ai-hunter-payload-code');
            if (payloadCode) {
                copyToClipboard(payloadCode.textContent);
                showNotification('Payload copied to clipboard', 'success');
            }
        });
    }
}

function generateAIHunterPayloadUI() {
    const agentSelect = document.getElementById('ai-hunter-agent-select');
    const targetType = document.getElementById('ai-hunter-target-type').value;
    const targetInput = document.getElementById('ai-hunter-target-input');
    const payloadType = document.getElementById('ai-hunter-payload-type').value;
    const debugMode = document.getElementById('ai-hunter-debug-mode').value === 'true';
    
    if (!agentSelect.value) {
        showNotification('Please select a target agent', 'warning');
        return;
    }
    
    const target = targetType === 'custom' ? targetInput.value : 'localhost';
    
    if (targetType === 'custom' && !target) {
        showNotification('Please enter a target IP/hostname', 'warning');
        return;
    }
    
    // Get custom ports if provided
    const customPorts = document.getElementById('ai-hunter-custom-ports').value;
    const ports = customPorts ? customPorts.split(',').map(p => parseInt(p.trim())) : null;
    
    // Get custom credentials if provided
    const customCreds = document.getElementById('ai-hunter-custom-creds').value;
    let credentials = null;
    if (customCreds) {
        try {
            credentials = JSON.parse(customCreds);
        } catch (e) {
            showNotification('Invalid JSON format for credentials', 'error');
            return;
        }
    }
    
    // Get custom prompts if provided
    const customPrompts = document.getElementById('ai-hunter-custom-prompts').value;
    let prompts = null;
    if (customPrompts) {
        try {
            prompts = JSON.parse(customPrompts);
        } catch (e) {
            showNotification('Invalid JSON format for prompts', 'error');
            return;
        }
    }
    
    const strategy = (document.getElementById('ai-hunter-selected-strategy') || {}).value || 'role_bypass';

    // Call backend to generate
    const config = {
        target: target,
        ports: ports,
        credentials: credentials,
        prompts: prompts,
        payload_type: payloadType,
        debug: debugMode,
        strategy: strategy
    };

    fetch('/ai_hunter/generate_payload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    })
    .then(r => r.json())
    .then(data => {
        if (data.status !== 'success') throw new Error(data.message || 'Generation failed');

        const payloadCode = document.getElementById('ai-hunter-payload-code');
        if (payloadCode) payloadCode.textContent = data.payload;

        const payloadPreview = document.getElementById('ai-hunter-payload-preview');
        if (payloadPreview) payloadPreview.style.display = 'block';

        const deployBtn = document.getElementById('ai-hunter-deploy-btn');
        if (deployBtn) deployBtn.style.display = 'block';

        // Activate discover phase
        const discoverPhase = document.getElementById('phase-discover');
        if (discoverPhase) discoverPhase.classList.add('active');

        showNotification('AI Hunter payload generated', 'success');
    })
    .catch(e => showNotification('Generation failed: ' + e.message, 'error'));
}

function deployAIHunterFromUI() {
    const agentSelect = document.getElementById('ai-hunter-agent-select');
    const payloadCode = document.getElementById('ai-hunter-payload-code');
    
    if (!agentSelect.value) {
        showNotification('Please select a target agent', 'warning');
        return;
    }
    
    if (!payloadCode || !payloadCode.textContent) {
        showNotification('Please generate a payload first', 'warning');
        return;
    }
    
    const config = {
        agent_id: agentSelect.value,
        payload: payloadCode.textContent
    };
    
    updateAIHunterStatus('HUNTING');

    fetch('/ai_hunter/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    })
    .then(r => r.json())
    .then(data => {
        if (data.status !== 'success') throw new Error(data.message || 'Deploy failed');
        showNotification('AI Hunter deployed to agent', 'success');
        updateAIHunterStatus('DEPLOYED');
    })
    .catch(e => showNotification('Deploy error: ' + e.message, 'error'));
}

// ========== MALWARE STUDIO INITIALIZATION ==========
function initializeMalwareStudio() {
    // Generate script button
    const generateBtn = document.getElementById('generate-script-btn');
    if (generateBtn) {
        generateBtn.addEventListener('click', generateScript);
    }
    
    // Copy generated code button
    const copyBtn = document.getElementById('copy-generated-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', function() {
            const codeDisplay = document.getElementById('generated-code-display');
            if (codeDisplay) {
                copyToClipboard(codeDisplay.textContent);
                showNotification('Code copied to clipboard', 'success');
            }
        });
    }
    
    // Edit generated code button
    const editBtn = document.getElementById('edit-generated-btn');
    if (editBtn) {
        editBtn.addEventListener('click', function() {
            // TODO: Implement edit functionality
            showNotification('Edit functionality coming soon', 'info');
        });
    }
    
    // Save to library button
    const saveBtn = document.getElementById('save-to-library-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', showSaveLibraryModal);
    }
    
    // Deploy generated button
    const deployBtn = document.getElementById('deploy-generated-btn');
    if (deployBtn) {
        deployBtn.addEventListener('click', function() {
            // TODO: Implement deploy functionality
            showNotification('Deploy functionality coming soon', 'info');
        });
    }
    
    // Library search
    const searchInput = document.getElementById('library-search');
    if (searchInput) {
        searchInput.addEventListener('input', filterLibrary);
    }
    
    // Library filter
    const filterSelect = document.getElementById('library-filter');
    if (filterSelect) {
        filterSelect.addEventListener('change', filterLibrary);
    }
}

function generateScript() {
    const description = document.getElementById('studio-description').value.trim();
    const language = document.getElementById('studio-language').value;
    const badge = document.getElementById('generated-lang-badge');

    if (!description) {
        showNotification('Describe the reconnaissance objective', 'warning');
        return;
    }

    const genBtn = document.getElementById('generate-script-btn');
    if (genBtn) { genBtn.disabled = true; genBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> GENERATING...'; }

    fetch('/studio/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, language })
    })
    .then(r => r.json())
    .then(data => {
        if (data.code) {
            displayGeneratedCode(data.code, language);
            if (badge) badge.textContent = language.toUpperCase();
            showNotification('Script generated successfully', 'success');
        } else {
            throw new Error(data.message || 'No code returned');
        }
    })
    .catch(e => {
        console.error('Script generation error:', e);
        showNotification('Generation failed: ' + e.message, 'error');
    })
    .finally(() => {
        if (genBtn) { genBtn.disabled = false; genBtn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i> GENERATE SCRIPT'; }
    });
}

function displayGeneratedCode(code, language) {
    const codeDisplay = document.getElementById('generated-code-display');
    const codeSection = document.getElementById('generated-code-section');
    
    if (codeDisplay && codeSection) {
        codeDisplay.textContent = code;
        codeSection.style.display = 'block';
        
        // Store for later use
        codeSection.dataset.generatedCode = code;
        codeSection.dataset.language = language;
    }
}

function showSaveLibraryModal() {
    // Quick save using auto-generated name + category from the studio UI
    const codeSection = document.getElementById('generated-code-section');
    const code = codeSection ? codeSection.dataset.generatedCode : '';
    const language = codeSection ? codeSection.dataset.language : 'powershell';
    const categoryEl = document.getElementById('studio-category');
    const category = categoryEl ? categoryEl.value : 'reconnaissance';
    const description = (document.getElementById('studio-description') || {}).value || '';

    if (!code) { showNotification('Generate a script first', 'warning'); return; }

    const name = 'Recon-' + language + '-' + new Date().toISOString().slice(0,10);

    fetch('/studio/library/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, code, language, category })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            showNotification('Script saved to library', 'success');
            loadScriptLibrary();
        } else {
            throw new Error(data.message);
        }
    })
    .catch(e => showNotification('Save failed: ' + e.message, 'error'));
}

function hideSaveLibraryModal() {
    const modal = document.getElementById('saveLibraryModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

function saveScriptToLibrary() {
    const name = document.getElementById('save-script-name').value.trim();
    const description = document.getElementById('save-script-description').value.trim();
    const category = document.getElementById('save-script-category').value;
    const tags = document.getElementById('save-script-tags').value.trim();
    
    const codeSection = document.getElementById('generated-code-section');
    const code = codeSection ? codeSection.dataset.generatedCode : '';
    const language = codeSection ? codeSection.dataset.language : 'python';
    
    if (!name) {
        showNotification('Please enter a script name', 'warning');
        return;
    }
    
    if (!code) {
        showNotification('No code to save', 'error');
        return;
    }
    
    const script = {
        id: generateUUID(),
        name: name,
        description: description,
        category: category,
        tags: tags.split(',').map(t => t.trim()).filter(t => t),
        language: language,
        code: code,
        created: new Date().toISOString(),
        updated: new Date().toISOString()
    };
    
    // Add to library
    scriptLibrary.push(script);
    saveScriptLibraryToStorage();
    
    // Update UI
    renderScriptLibrary();
    updateLibraryCount();
    
    // Close modal
    hideSaveLibraryModal();
    
    // Clear form
    document.getElementById('save-script-name').value = '';
    document.getElementById('save-script-description').value = '';
    document.getElementById('save-script-tags').value = '';
    
    showNotification('Script saved to library', 'success');
}

function loadScriptLibrary() {
    const stored = localStorage.getItem('script_library');
    if (stored) {
        try {
            scriptLibrary = JSON.parse(stored);
            renderScriptLibrary();
            updateLibraryCount();
        } catch (e) {
            console.error('Error loading script library:', e);
            scriptLibrary = [];
        }
    }
}

function saveScriptLibraryToStorage() {
    localStorage.setItem('script_library', JSON.stringify(scriptLibrary));
}

function renderScriptLibrary() {
    const grid = document.getElementById('library-grid');
    if (!grid) return;
    
    // Clear grid
    grid.innerHTML = '';
    
    if (scriptLibrary.length === 0) {
        grid.innerHTML = `
            <div class="empty-library">
                <i class="fas fa-folder-open"></i>
                <p>No scripts in library yet</p>
                <p class="hint">Generate and save scripts to build your library</p>
            </div>
        `;
        return;
    }
    
    // Render scripts
    scriptLibrary.forEach(script => {
        const card = createScriptCard(script);
        grid.appendChild(card);
    });
}

function createScriptCard(script) {
    const card = document.createElement('div');
    card.className = 'script-card';
    card.onclick = () => showScriptDetail(script.id);
    
    const languageClass = script.language.toLowerCase();
    
    card.innerHTML = `
        <div class="script-card-header">
            <h4 class="script-name">${escapeHtml(script.name)}</h4>
            <span class="script-language ${languageClass}">${escapeHtml(script.language)}</span>
        </div>
        <p class="script-description">${escapeHtml(script.description || 'No description')}</p>
        <div class="script-meta">
            <span class="script-category">${escapeHtml(script.category)}</span>
            <span class="script-date">${formatDate(script.created)}</span>
        </div>
    `;
    
    return card;
}

function showScriptDetail(scriptId) {
    const script = scriptLibrary.find(s => s.id === scriptId);
    if (!script) return;
    
    // Populate modal
    document.getElementById('detail-script-name').textContent = script.name;
    document.getElementById('detail-script-language').textContent = script.language;
    document.getElementById('detail-script-category').textContent = script.category;
    document.getElementById('detail-script-created').textContent = formatDate(script.created);
    document.getElementById('detail-script-updated').textContent = formatDate(script.updated);
    document.getElementById('detail-script-description').textContent = script.description || 'No description';
    document.getElementById('detail-script-code').textContent = script.code;
    
    // Render tags
    const tagsContainer = document.getElementById('detail-script-tags');
    tagsContainer.innerHTML = '';
    if (script.tags && script.tags.length > 0) {
        script.tags.forEach(tag => {
            const tagSpan = document.createElement('span');
            tagSpan.className = 'tag';
            tagSpan.textContent = tag;
            tagsContainer.appendChild(tagSpan);
        });
    } else {
        tagsContainer.innerHTML = '<span style="color: #6c757d;">No tags</span>';
    }
    
    // Store current script ID for actions
    const modal = document.getElementById('scriptDetailModal');
    if (modal) {
        modal.dataset.currentScriptId = scriptId;
        modal.classList.add('show');
    }
}

function hideScriptDetailModal() {
    const modal = document.getElementById('scriptDetailModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

function copyScriptCode() {
    const code = document.getElementById('detail-script-code').textContent;
    copyToClipboard(code);
    showNotification('Code copied to clipboard', 'success');
}

function deployScriptFromLibrary() {
    const modal = document.getElementById('scriptDetailModal');
    const scriptId = modal ? modal.dataset.currentScriptId : null;
    
    if (!scriptId) return;
    
    // Show deploy modal
    hideScriptDetailModal();
    const deployModal = document.getElementById('deployScriptModal');
    if (deployModal) {
        deployModal.dataset.scriptId = scriptId;
        deployModal.classList.add('show');
    }
}

function hideDeployScriptModal() {
    const modal = document.getElementById('deployScriptModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

function confirmDeployScript() {
    const modal = document.getElementById('deployScriptModal');
    const scriptId = modal ? modal.dataset.scriptId : null;
    const agentSelect = document.getElementById('deploy-script-agent');
    
    if (!scriptId || !agentSelect || !agentSelect.value) {
        showNotification('Please select a target agent', 'warning');
        return;
    }
    
    const script = scriptLibrary.find(s => s.id === scriptId);
    if (!script) return;
    
    // Deploy script
    const taskData = {
        agent_id: agentSelect.value,
        task_type: 'custom',
        code: script.code,
        metadata: {
            script_name: script.name,
            language: script.language
        }
    };
    
    fetch('/api/tasks', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + getAuthToken()
        },
        body: JSON.stringify(taskData)
    })
    .then(response => response.json())
    .then(data => {
        showNotification(`Script "${script.name}" deployed to ${agentSelect.value}`, 'success');
        hideDeployScriptModal();
    })
    .catch(error => {
        console.error('Error deploying script:', error);
        showNotification('Failed to deploy script: ' + error.message, 'error');
    });
}

function deleteScriptFromLibrary() {
    const modal = document.getElementById('scriptDetailModal');
    const scriptId = modal ? modal.dataset.currentScriptId : null;
    
    if (!scriptId) return;
    
    if (!confirm('Are you sure you want to delete this script?')) return;
    
    // Remove from library
    scriptLibrary = scriptLibrary.filter(s => s.id !== scriptId);
    saveScriptLibraryToStorage();
    
    // Update UI
    renderScriptLibrary();
    updateLibraryCount();
    hideScriptDetailModal();
    
    showNotification('Script deleted', 'success');
}

function filterLibrary() {
    const searchTerm = document.getElementById('library-search').value.toLowerCase();
    const category = document.getElementById('library-filter').value;
    
    const filtered = scriptLibrary.filter(script => {
        const matchesSearch = !searchTerm || 
            script.name.toLowerCase().includes(searchTerm) ||
            script.description.toLowerCase().includes(searchTerm) ||
            (script.tags && script.tags.some(tag => tag.toLowerCase().includes(searchTerm)));
        
        const matchesCategory = category === 'all' || script.category === category;
        
        return matchesSearch && matchesCategory;
    });
    
    // Render filtered results
    const grid = document.getElementById('library-grid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    if (filtered.length === 0) {
        grid.innerHTML = `
            <div class="empty-library">
                <i class="fas fa-search"></i>
                <p>No scripts found</p>
                <p class="hint">Try adjusting your search or filter</p>
            </div>
        `;
        return;
    }
    
    filtered.forEach(script => {
        const card = createScriptCard(script);
        grid.appendChild(card);
    });
}

function updateLibraryCount() {
    const countElement = document.getElementById('library-count');
    if (countElement) {
        const count = scriptLibrary.length;
        countElement.textContent = `${count} script${count !== 1 ? 's' : ''}`;
    }
}

// ========== OBFUSCATOR INITIALIZATION ==========
function initializeObfuscator() {
    const obfuscateBtn = document.getElementById('obfuscate-btn');
    if (obfuscateBtn) {
        obfuscateBtn.addEventListener('click', obfuscateCode);
    }
    
    const deployObfuscatedBtn = document.getElementById('deploy-obfuscated');
    if (deployObfuscatedBtn) {
        deployObfuscatedBtn.addEventListener('click', function() {
            showDeployModal();
        });
    }
    
    const copyObfuscatedBtn = document.getElementById('copy-obfuscated');
    if (copyObfuscatedBtn) {
        copyObfuscatedBtn.addEventListener('click', function() {
            const obfuscatedCode = document.getElementById('obfuscated-code');
            if (obfuscatedCode) {
                copyToClipboard(obfuscatedCode.textContent);
                showNotification('Obfuscated code copied to clipboard', 'success');
            }
        });
    }
}

function obfuscateCode() {
    const originalCode = document.getElementById('original-code').value.trim();
    const language = document.getElementById('code-language').value;
    const targetSecurity = document.getElementById('target-security').value;
    
    if (!originalCode) {
        showNotification('Please enter code to obfuscate', 'warning');
        return;
    }
    
    showNotification('Obfuscating code...', 'info');
    
    // Call backend to obfuscate
    fetch('/api/obfuscate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + getAuthToken()
        },
        body: JSON.stringify({
            code: originalCode,
            language: language,
            target_security: targetSecurity
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.obfuscated_code) {
            document.getElementById('obfuscated-code').textContent = data.obfuscated_code;
            
            if (data.explanation) {
                const resultDiv = document.getElementById('obfuscation-result');
                const explanationDiv = document.getElementById('obfuscation-explanation');
                if (resultDiv && explanationDiv) {
                    explanationDiv.innerHTML = data.explanation.replace(/\n/g, '<br>');
                    resultDiv.style.display = 'block';
                }
            }
            
            showNotification('Code obfuscated successfully', 'success');
        } else {
            throw new Error('No obfuscated code returned');
        }
    })
    .catch(error => {
        console.error('Error obfuscating code:', error);
        showNotification('Failed to obfuscate code: ' + error.message, 'error');
    });
}

// ========== ATTACK VECTORS INITIALIZATION ==========
function initializeAttackVectors() {
    // Replaced by AutoRecon — see initializeAutoRecon() below
    initializeAutoRecon();
}

// ========== TASK MODAL ==========
function showTaskModal(agentId) {
    document.getElementById('agent_id').value = agentId;
    const modal = document.getElementById('taskModal');
    if (modal) {
        modal.classList.add('show');
    }
    
    // Handle custom code visibility
    const taskTypeSelect = document.getElementById('task_type');
    if (taskTypeSelect) {
        taskTypeSelect.addEventListener('change', function() {
            const customBlock = document.getElementById('customCodeBlock');
            if (customBlock) {
                customBlock.style.display = this.value === 'custom' ? 'block' : 'none';
            }
        });
    }
}

function hideTaskModal() {
    const modal = document.getElementById('taskModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

function submitTask() {
    const agentId = document.getElementById('agent_id').value;
    const taskType = document.getElementById('task_type').value;
    let customCode = '';
    
    if (taskType === 'custom') {
        customCode = document.getElementById('custom_code').value.trim();
        if (!customCode) {
            showNotification('Please enter custom code', 'warning');
            return;
        }
    }
    
    const taskData = {
        agent_id: agentId,
        task_type: taskType,
        code: customCode
    };
    
    fetch('/api/tasks', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + getAuthToken()
        },
        body: JSON.stringify(taskData)
    })
    .then(response => response.json())
    .then(data => {
        showNotification('Task created successfully', 'success');
        hideTaskModal();
        // Refresh dashboard
        setTimeout(() => location.reload(), 1000);
    })
    .catch(error => {
        console.error('Error creating task:', error);
        showNotification('Failed to create task: ' + error.message, 'error');
    });
}

// ========== PAYLOAD VIEWER MODAL ==========
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('view-payload-btn')) {
        const payload = e.target.dataset.payload;
        if (payload) {
            try {
                const payloadObj = JSON.parse(payload);
                showPayloadModal(JSON.stringify(payloadObj, null, 2));
            } catch (err) {
                showPayloadModal(payload);
            }
        }
    }
    
    if (e.target.classList.contains('view-intel-btn')) {
        const intel = e.target.dataset.intel;
        if (intel) {
            try {
                const intelObj = JSON.parse(intel);
                showIntelModal(JSON.stringify(intelObj, null, 2));
            } catch (err) {
                showIntelModal(intel);
            }
        }
    }
    
    if (e.target.classList.contains('ai-analyze-btn')) {
        const intel = e.target.dataset.intel;
        if (intel) {
            analyzeIntelWithAI(intel);
        }
    }
});

function showPayloadModal(payload) {
    const modal = document.getElementById('payloadModal');
    const content = document.getElementById('payload-content');
    if (modal && content) {
        content.textContent = payload;
        modal.classList.add('show');
    }
}

function hidePayloadModal() {
    const modal = document.getElementById('payloadModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

function showIntelModal(intel) {
    const modal = document.getElementById('intelModal');
    const content = document.getElementById('intel-content');
    if (modal && content) {
        content.textContent = intel;
        modal.classList.add('show');
    }
}

function hideIntelModal() {
    const modal = document.getElementById('intelModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

function analyzeIntelWithAI(intel) {
    showNotification('Analyzing intelligence with AI...', 'info');
    
    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + getAuthToken()
        },
        body: JSON.stringify({
            message: 'Analyze this intelligence data and identify potential attack vectors, credentials, and exploitation opportunities:',
            logs: intel
        })
    })
    .then(response => response.json())
    .then(data => {
        handleChatResponse(data);
        switchTab('terminal');
        showNotification('AI analysis complete', 'success');
    })
    .catch(error => {
        console.error('Error analyzing intel:', error);
        showNotification('Failed to analyze intel: ' + error.message, 'error');
    });
}

// ========== DEPLOY MODAL ==========
function showDeployModal() {
    const modal = document.getElementById('deployModal');
    if (modal) {
        modal.classList.add('show');
    }
}

function hideDeployModal() {
    const modal = document.getElementById('deployModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

function deployCode() {
    const agentSelect = document.getElementById('deploy-agent-select');
    const obfuscatedCode = document.getElementById('obfuscated-code');
    
    if (!agentSelect || !agentSelect.value) {
        showNotification('Please select a target agent', 'warning');
        return;
    }
    
    if (!obfuscatedCode || !obfuscatedCode.textContent) {
        showNotification('No code to deploy', 'error');
        return;
    }
    
    const taskData = {
        agent_id: agentSelect.value,
        task_type: 'custom',
        code: obfuscatedCode.textContent
    };
    
    fetch('/api/tasks', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + getAuthToken()
        },
        body: JSON.stringify(taskData)
    })
    .then(response => response.json())
    .then(data => {
        showNotification('Obfuscated code deployed successfully', 'success');
        hideDeployModal();
    })
    .catch(error => {
        console.error('Error deploying code:', error);
        showNotification('Failed to deploy code: ' + error.message, 'error');
    });
}

// ========== REFRESH FUNCTIONALITY ==========
document.getElementById('refresh-btn')?.addEventListener('click', function() {
    const modal = document.getElementById('refreshModal');
    if (modal) {
        modal.classList.add('show');
    }
});

function hideRefreshConfirmation() {
    const modal = document.getElementById('refreshModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

function refreshDashboard() {
    showNotification('Refreshing dashboard...', 'info');
    location.reload();
}

// ========== AI TOGGLE ==========
function initializeAIToggle() {
    const toggle = document.getElementById('ai-toggle-switch');
    const configToggle = document.getElementById('config-ai-toggle');
    
    if (toggle) {
        toggle.addEventListener('change', function() {
            updateAIMode(this.checked);
        });
    }
    
    if (configToggle) {
        configToggle.addEventListener('change', function() {
            updateAIMode(this.checked);
            // Sync with header toggle
            if (toggle) {
                toggle.checked = this.checked;
            }
        });
    }
}

function updateAIMode(enabled) {
    // Update UI indicators
    const statusIndicator = document.getElementById('ai-status-indicator');
    const sidebarStatus = document.getElementById('sidebar-ai-status');
    const configStatus = document.getElementById('config-ai-status');
    
    const statusText = enabled ? 'ENABLED' : 'DISABLED';
    
    if (statusIndicator) {
        statusIndicator.textContent = statusText;
        statusIndicator.className = enabled ? 'ai-status enabled' : 'ai-status disabled';
    }
    
    if (sidebarStatus) {
        sidebarStatus.textContent = statusText;
        sidebarStatus.className = enabled ? 'stat-value ai-mode-enabled' : 'stat-value ai-mode-disabled';
    }
    
    if (configStatus) {
        configStatus.textContent = statusText;
    }
    
    // Update all AI indicators
    document.querySelectorAll('.ai-indicator').forEach(indicator => {
        indicator.textContent = `AI: ${enabled ? 'ON' : 'OFF'}`;
        indicator.style.background = enabled ? '#28a745' : '#6c757d';
    });
    
    // Call backend to update setting
    fetch('/api/config/ai-mode', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + getAuthToken()
        },
        body: JSON.stringify({ enabled: enabled })
    })
    .then(response => response.json())
    .then(data => {
        showNotification(`AI Mode ${statusText}`, 'success');
    })
    .catch(error => {
        console.error('Error updating AI mode:', error);
        showNotification('Failed to update AI mode', 'error');
    });
}

// ========== NOTIFICATION SYSTEM ==========
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 8px;
        color: #fff;
        font-weight: 600;
        z-index: 10000;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        animation: slideInRight 0.3s ease-out;
        max-width: 400px;
    `;
    
    const colors = {
        'success': 'linear-gradient(135deg, #28a745, #20c997)',
        'error': 'linear-gradient(135deg, #dc3545, #c82333)',
        'warning': 'linear-gradient(135deg, #ffc107, #e0a800)',
        'info': 'linear-gradient(135deg, #0f3460, #16213e)'
    };
    
    const icons = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    };
    
    notification.style.background = colors[type] || colors['info'];
    
    notification.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <i class="fas ${icons[type] || icons['info']}" style="font-size: 1.2rem;"></i>
            <span>${escapeHtml(message)}</span>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// ========== UTILITY FUNCTIONS ==========
function getAuthToken() {
    return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token') || '';
}

function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text);
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
    }
}

function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'just now';
}

// ========== UPTIME COUNTER ==========
let uptimeSeconds = 0;

function startUptimeCounter() {
    setInterval(() => {
        uptimeSeconds++;
        const hours = Math.floor(uptimeSeconds / 3600);
        const minutes = Math.floor((uptimeSeconds % 3600) / 60);
        const seconds = uptimeSeconds % 60;
        
        const uptimeElement = document.getElementById('uptime');
        if (uptimeElement) {
            uptimeElement.textContent = 
                `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }
    }, 1000);
}

// ========== BEIJING TIME CLOCK ==========
function startBeijingClock() {
    function updateClock() {
        const now = new Date();
        const beijingTime = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }));
        const hours = String(beijingTime.getHours()).padStart(2, '0');
        const minutes = String(beijingTime.getMinutes()).padStart(2, '0');
        
        const clockElement = document.getElementById('beijing-time');
        if (clockElement) {
            clockElement.textContent = `${hours}:${minutes}`;
        }
    }
    
    updateClock();
    setInterval(updateClock, 60000); // Update every minute
}

// ========== CLOSE MODALS ON OUTSIDE CLICK ==========
window.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('show');
    }
});

console.log('NEURAL NEXUS JavaScript loaded successfully');

// ========== AUTORECON ==========
let autoReconSessionId = null;
let autoReconPollTimer = null;

function initializeAutoRecon() {
    const agentSelect = document.getElementById('autorecon-agent-select');
    const startBtn = document.getElementById('autorecon-start-btn');
    const stopBtn = document.getElementById('autorecon-stop-btn');

    if (agentSelect) {
        agentSelect.addEventListener('change', function() {
            if (startBtn) startBtn.disabled = !this.value;
        });
    }
    if (startBtn) startBtn.addEventListener('click', startAutoRecon);
    if (stopBtn) stopBtn.addEventListener('click', stopAutoRecon);

    loadAutoReconSessions();
}

function startAutoRecon() {
    const agentId = document.getElementById('autorecon-agent-select').value;
    const goal = document.getElementById('autorecon-goal').value.trim();
    const language = document.getElementById('autorecon-language').value;
    const maxSteps = parseInt(document.getElementById('autorecon-max-steps').value);

    if (!agentId) { showNotification('Select a target agent', 'warning'); return; }
    if (!goal) { showNotification('Enter a reconnaissance goal', 'warning'); return; }

    fetch('/autorecon/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId, goal, language, max_steps: maxSteps })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            autoReconSessionId = data.session_id;
            showNotification('AutoRecon session started', 'success');
            document.getElementById('autorecon-start-btn').style.display = 'none';
            document.getElementById('autorecon-stop-btn').style.display = 'block';
            renderAutoReconChain(null);
            pollAutoRecon();
        } else {
            showNotification('Failed to start: ' + data.message, 'error');
        }
    })
    .catch(e => showNotification('Error: ' + e.message, 'error'));
}

function pollAutoRecon() {
    if (!autoReconSessionId) return;
    if (autoReconPollTimer) clearTimeout(autoReconPollTimer);

    fetch('/autorecon/status/' + autoReconSessionId)
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            const session = data.session;
            renderAutoReconChain(session);
            updateAutoReconStatus(session);

            if (session.status === 'running') {
                autoReconPollTimer = setTimeout(pollAutoRecon, 4000);
            } else {
                document.getElementById('autorecon-start-btn').style.display = 'block';
                document.getElementById('autorecon-stop-btn').style.display = 'none';
                loadAutoReconSessions();
            }
        }
    })
    .catch(e => { autoReconPollTimer = setTimeout(pollAutoRecon, 5000); });
}

function stopAutoRecon() {
    if (!autoReconSessionId) return;
    fetch('/autorecon/stop/' + autoReconSessionId, { method: 'POST' })
    .then(r => r.json())
    .then(() => {
        if (autoReconPollTimer) clearTimeout(autoReconPollTimer);
        document.getElementById('autorecon-start-btn').style.display = 'block';
        document.getElementById('autorecon-stop-btn').style.display = 'none';
        showNotification('AutoRecon stopped', 'success');
        loadAutoReconSessions();
    });
}

function updateAutoReconStatus(session) {
    const statusEl = document.getElementById('autorecon-session-status');
    const progressFill = document.getElementById('autorecon-progress-fill');
    const progressLabel = document.getElementById('autorecon-progress-label');
    const progressBar = document.getElementById('autorecon-progress-bar');
    const goalDisplay = document.getElementById('autorecon-goal-display');
    const goalText = document.getElementById('autorecon-goal-text');

    if (goalDisplay) goalDisplay.style.display = 'flex';
    if (goalText) goalText.textContent = session.goal;
    if (progressBar) progressBar.style.display = 'flex';

    const pct = session.max_steps > 0 ? Math.round((session.current_step / session.max_steps) * 100) : 0;
    if (progressFill) progressFill.style.width = pct + '%';
    if (progressLabel) progressLabel.textContent = session.current_step + ' / ' + session.max_steps;

    const statusColors = { running: 'var(--accent-cyan)', completed: 'var(--accent-green)', stopped: 'var(--accent-amber)', error: 'var(--accent-red)' };
    if (statusEl) {
        statusEl.textContent = session.status.toUpperCase();
        statusEl.style.color = statusColors[session.status] || 'var(--text-muted)';
    }
}

function renderAutoReconChain(session) {
    const chain = document.getElementById('autorecon-chain');
    if (!chain) return;

    if (!session || session.steps.length === 0) {
        if (session && session.status === 'running') {
            chain.innerHTML = `<div style="text-align:center;padding:40px;color:var(--accent-cyan);">
                <i class="fas fa-spinner fa-spin" style="font-size:2rem;margin-bottom:12px;display:block;"></i>
                <p style="font-size:0.88rem;">Generating first reconnaissance script...</p>
            </div>`;
        }
        return;
    }

    let html = '';
    session.steps.forEach((step, idx) => {
        const isLast = idx === session.steps.length - 1;
        const dotClass = step.status === 'completed' ? 'completed' : step.status === 'pending' && session.status === 'running' ? 'running' : 'pending';
        const badgeClass = dotClass;
        const lineClass = step.status === 'completed' ? 'active' : '';
        const icon = step.status === 'completed' ? '<i class="fas fa-check"></i>' : step.status === 'pending' && session.status === 'running' ? '<i class="fas fa-spinner fa-spin"></i>' : step.step_num;

        html += `<div class="autorecon-step">
            <div class="step-connector">
                <div class="step-dot ${dotClass}">${icon}</div>
                ${!isLast ? `<div class="step-line ${lineClass}"></div>` : ''}
            </div>
            <div class="step-content">
                <div class="step-header">
                    <span class="step-title">Step ${step.step_num}: ${step.language.toUpperCase()} Recon</span>
                    <span class="step-status-badge ${badgeClass}">${step.status}</span>
                </div>
                <div class="step-reasoning">${step.reasoning || 'AI-generated recon script'}</div>
                <button class="step-script-toggle" onclick="toggleStepScript(this,'script-${step.step_num}')">
                    <i class="fas fa-code"></i> View Script
                </button>
                <div id="script-${step.step_num}" class="step-script-block" style="display:none;">${escapeHtml(step.script || '')}</div>
                ${step.result ? `
                <button class="step-script-toggle" style="margin-top:4px;" onclick="toggleStepScript(this,'result-${step.step_num}')">
                    <i class="fas fa-chart-bar"></i> View Results
                </button>
                <div id="result-${step.step_num}" class="step-result-block" style="display:none;">${escapeHtml(step.result)}</div>` : ''}
            </div>
        </div>`;
    });

    if (session.status === 'running' && session.steps.length < session.max_steps) {
        html += `<div class="autorecon-step">
            <div class="step-connector">
                <div class="step-dot pending"><i class="fas fa-ellipsis-h"></i></div>
            </div>
            <div class="step-content">
                <div class="step-header"><span class="step-title" style="color:var(--text-muted);">Next steps pending...</span></div>
            </div>
        </div>`;
    }

    chain.innerHTML = html;
}

function toggleStepScript(btn, targetId) {
    const block = document.getElementById(targetId);
    if (!block) return;
    const isHidden = block.style.display === 'none';
    block.style.display = isHidden ? 'block' : 'none';
    btn.innerHTML = isHidden
        ? '<i class="fas fa-eye-slash"></i> Hide'
        : (targetId.startsWith('result') ? '<i class="fas fa-chart-bar"></i> View Results' : '<i class="fas fa-code"></i> View Script');
}

function loadAutoReconSessions() {
    fetch('/autorecon/sessions')
    .then(r => r.json())
    .then(data => {
        const list = document.getElementById('autorecon-sessions-list');
        if (!list) return;
        if (!data.sessions || data.sessions.length === 0) {
            list.innerHTML = '<div style="color:var(--text-muted);font-size:0.82rem;text-align:center;padding:20px;">No sessions yet</div>';
            return;
        }
        const statusColor = { running: 'var(--accent-cyan)', completed: 'var(--accent-green)', stopped: 'var(--accent-amber)', error: 'var(--accent-red)' };
        list.innerHTML = data.sessions.map(s => `
            <div style="padding:10px 0;border-bottom:1px solid var(--border-subtle);cursor:pointer;" onclick="loadAutoReconSession('${s.id}')">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="font-family:monospace;font-size:0.75rem;color:var(--accent-cyan);">${s.id.substring(0,8)}...</span>
                    <span style="font-size:0.7rem;font-weight:600;color:${statusColor[s.status]||'var(--text-muted)'};">${s.status.toUpperCase()}</span>
                </div>
                <div style="color:var(--text-secondary);font-size:0.8rem;margin-bottom:2px;">${s.goal}</div>
                <div style="color:var(--text-muted);font-size:0.75rem;">${s.current_step}/${s.max_steps} steps · ${s.agent_id.substring(0,8)}...</div>
            </div>
        `).join('');
    })
    .catch(() => {});
}

function loadAutoReconSession(sessionId) {
    autoReconSessionId = sessionId;
    fetch('/autorecon/status/' + sessionId)
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            const session = data.session;
            renderAutoReconChain(session);
            updateAutoReconStatus(session);
            if (session.status === 'running') pollAutoRecon();
        }
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text || ''));
    return div.innerHTML;
}

// ========== AI HUNTER IMPROVEMENTS ==========
function selectInjectionStrategy(el, strategy) {
    document.querySelectorAll('.injection-strategy-card').forEach(c => c.classList.remove('selected'));
    el.classList.add('selected');
    const hidden = document.getElementById('ai-hunter-selected-strategy');
    if (hidden) hidden.value = strategy;
}

function renderHunterResults(data) {
    const resultsDiv = document.getElementById('ai-hunter-results');
    const emptyState = document.getElementById('hunter-empty-state');
    const statusEl = document.getElementById('hunter-result-status');

    if (!resultsDiv) return;

    // Parse JSON result if it's a string
    let report = data;
    if (typeof data === 'string') {
        try { report = JSON.parse(data); } catch(e) { report = { raw: data }; }
    }

    const endpoints = report.endpoints || [];
    const sessions = report.sessions || [];
    const docs = report.docs || [];
    const llm_responses = report.llm_responses || [];

    // Summary metrics
    const summaryDiv = document.getElementById('ai-hunter-summary');
    if (summaryDiv) {
        summaryDiv.innerHTML = [
            { label: 'Endpoints Found', value: endpoints.length, color: 'var(--accent-cyan)' },
            { label: 'Auth Compromised', value: sessions.length, color: 'var(--accent-red)' },
            { label: 'Docs Accessed', value: docs.length, color: 'var(--accent-amber)' },
            { label: 'LLM Responses', value: llm_responses.length, color: 'var(--accent-purple)' }
        ].map(m => `
            <div style="background:rgba(255,255,255,0.03);border:1px solid var(--border-subtle);border-radius:8px;padding:14px;text-align:center;">
                <div style="font-size:1.6rem;font-weight:700;color:${m.color};">${m.value}</div>
                <div style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;margin-top:4px;">${m.label}</div>
            </div>
        `).join('');
    }

    // Sessions list
    const sessionsList = document.getElementById('hunter-sessions-list');
    if (sessionsList) {
        sessionsList.innerHTML = sessions.length === 0
            ? '<div style="color:var(--text-muted);font-size:0.82rem;">No sessions authenticated</div>'
            : sessions.map(s => `
                <div style="background:rgba(168,85,247,0.06);border:1px solid rgba(168,85,247,0.2);border-radius:7px;padding:10px;margin-bottom:8px;">
                    <div style="display:flex;gap:12px;flex-wrap:wrap;">
                        <span style="color:var(--accent-purple);font-weight:600;">${s.username || '?'}</span>
                        <span style="color:var(--text-muted);font-size:0.8rem;">Role: ${s.role || 'unknown'}</span>
                        <span style="color:var(--text-muted);font-size:0.8rem;">Scopes: ${(s.scopes||[]).join(', ') || 'none'}</span>
                    </div>
                </div>`).join('');
    }

    // LLM injection results
    const detailedDiv = document.getElementById('ai-hunter-detailed-results');
    if (detailedDiv) {
        detailedDiv.innerHTML = llm_responses.length === 0
            ? '<div style="color:var(--text-muted);font-size:0.82rem;">No LLM responses captured</div>'
            : llm_responses.map(r => `
                <div style="background:rgba(0,0,0,0.2);border:1px solid var(--border-subtle);border-radius:7px;padding:12px;margin-bottom:10px;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                        <span style="color:var(--accent-purple);font-size:0.8rem;font-weight:600;"><i class="fas fa-user"></i> ${r.user || '?'}</span>
                        <span style="color:var(--accent-amber);font-size:0.72rem;">INJECTION RESULT</span>
                    </div>
                    <div style="color:var(--text-muted);font-size:0.78rem;margin-bottom:6px;font-style:italic;">"${r.prompt || ''}"</div>
                    <div style="color:var(--text-primary);font-size:0.82rem;background:rgba(255,255,255,0.03);padding:8px;border-radius:5px;font-family:monospace;">${r.reply || 'No response'}</div>
                </div>`).join('');
    }

    if (emptyState) emptyState.style.display = 'none';
    resultsDiv.style.display = 'block';
    if (statusEl) { statusEl.textContent = 'Results received'; statusEl.style.color = 'var(--accent-green)'; }

    // Update phase bar
    updateHunterPhases(sessions.length > 0, llm_responses.length > 0);
}

function updateHunterPhases(authDone, injectDone) {
    const phases = ['phase-discover', 'phase-auth', 'phase-map', 'phase-inject', 'phase-extract'];
    const done = [true, authDone, authDone, injectDone, injectDone];
    phases.forEach((id, i) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.className = 'phase-node' + (done[i] ? ' done' : (i === (done.indexOf(false)) ? ' active' : ''));
    });
}

// Hook into existing deployAIHunterPayload to render results
const _origDeploy = typeof deployAIHunterPayload !== 'undefined' ? deployAIHunterPayload : null;

// ========== RECON STUDIO: update lang badge on generate ==========
const _origGenerateStudio = typeof generateScript !== 'undefined' ? generateScript : null;

document.addEventListener('DOMContentLoaded', function() {
    // Update lang badge after generation
    const genBtn = document.getElementById('generate-script-btn');
    if (genBtn) {
        genBtn.addEventListener('click', function() {
            const lang = document.getElementById('studio-language');
            const badge = document.getElementById('generated-lang-badge');
            if (lang && badge) badge.textContent = lang.value.toUpperCase();
        }, true); // capture phase so it runs before the existing handler
    }
}, { once: true });
