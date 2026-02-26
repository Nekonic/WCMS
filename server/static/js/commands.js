// 일괄 명령, 결과 추적, 대기 명령, 중복 PC 관리 (index.html에서 추출)
// 의존 전역변수: selectedPCs, allPCs (pc-grid.js에서 초기화됨)

// ==================== 일괄 명령 모달 함수 ====================

function showBulkCMDModal() {
    const cmd = prompt('실행할 CMD 명령어를 입력하세요:\n\n예시:\n- hostname\n- whoami\n- ipconfig\n- dir');
    if (!cmd) return;
    executeBulkCommand('execute', { command: cmd });
}

function showBulkMessageModal() {
    const message = prompt('표시할 메시지를 입력하세요:');
    if (!message) return;
    executeBulkCommand('message', { message: message });
}

async function showBulkKillProcessModal() {
    try {
        const response = await fetch('/api/admin/processes');
        const data = await response.json();

        if (!response.ok) { alert('프로세스 목록을 불러올 수 없습니다.'); return; }

        const processes = data.processes || [];
        document.body.insertAdjacentHTML('beforeend', `
            <div id="killProcessModal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);z-index:2000;display:flex;align-items:center;justify-content:center;padding:2em;">
                <div style="background:#2a2a2a;border-radius:12px;padding:2em;max-width:500px;width:100%;color:white;">
                    <h3 style="margin-top:0;margin-bottom:1em;">프로세스 종료</h3>
                    <p style="color:#aaa;margin-bottom:1em;">종료할 프로세스를 선택하거나 입력하세요.</p>
                    <div style="margin-bottom:1.5em;">
                        <input type="text" id="processInput" list="processList" placeholder="프로세스 이름 (예: chrome.exe)" style="width:100%;padding:0.8em;border-radius:6px;border:1px solid #444;background:#333;color:white;font-size:1em;">
                        <datalist id="processList">${processes.map(p => `<option value="${p}">`).join('')}</datalist>
                    </div>
                    <div style="display:flex;justify-content:flex-end;gap:1em;">
                        <button onclick="document.getElementById('killProcessModal').remove()" style="background:transparent;color:#aaa;border:1px solid #444;padding:0.6em 1.2em;border-radius:6px;cursor:pointer;">취소</button>
                        <button onclick="confirmKillProcess()" style="background:#dc2626;color:white;border:none;padding:0.6em 1.2em;border-radius:6px;cursor:pointer;font-weight:600;">종료</button>
                    </div>
                </div>
            </div>
        `);
        document.getElementById('processInput').focus();
    } catch (error) {
        console.error('Load processes error:', error);
        alert('프로세스 목록을 불러오는 중 오류가 발생했습니다.');
    }
}

function confirmKillProcess() {
    const processName = document.getElementById('processInput').value.trim();
    if (!processName) { alert('프로세스 이름을 입력하세요.'); return; }
    document.getElementById('killProcessModal').remove();
    executeBulkCommand('kill_process', { process_name: processName });
}

function showBulkChocoModal() {
    const appId = prompt('설치할 프로그램의 Chocolatey 패키지 ID를 입력하세요:\n\n예시:\n- googlechrome\n- notepadplusplus\n- 7zip\n- vlc');
    if (!appId) return;
    executeBulkCommand('install', { app_id: appId });
}

function showBulkFileDownloadModal() {
    const url = prompt('다운로드할 파일의 URL을 입력하세요:');
    if (!url) return;
    const path = prompt('저장할 경로를 입력하세요:\n(예: C:\\\\temp\\\\file.zip)', 'C:\\\\temp\\\\download.txt');
    if (!path) return;
    executeBulkCommand('download', { url, destination: path });
}

function showBulkAccountModal() {
    document.body.insertAdjacentHTML('beforeend', `
        <div id="accountModal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);z-index:2000;display:flex;align-items:center;justify-content:center;padding:2em;">
            <div style="background:#2a2a2a;border-radius:12px;padding:2em;max-width:500px;width:100%;color:white;">
                <h3 style="margin-top:0;margin-bottom:1em;">계정 관리</h3>
                <div style="margin-bottom:1.5em;">
                    <label style="display:block;margin-bottom:0.5em;color:#aaa;">작업 선택</label>
                    <select id="accountAction" onchange="updateAccountModalFields()" style="width:100%;padding:0.8em;border-radius:6px;border:1px solid #444;background:#333;color:white;font-size:1em;">
                        <option value="create_user">계정 생성</option>
                        <option value="delete_user">계정 삭제</option>
                        <option value="change_password">비밀번호 변경</option>
                    </select>
                </div>
                <div style="margin-bottom:1em;">
                    <label style="display:block;margin-bottom:0.5em;color:#aaa;">사용자 이름</label>
                    <input type="text" id="accountUsername" style="width:100%;padding:0.8em;border-radius:6px;border:1px solid #444;background:#333;color:white;font-size:1em;">
                </div>
                <div id="accountPasswordField" style="margin-bottom:1.5em;">
                    <label style="display:block;margin-bottom:0.5em;color:#aaa;">비밀번호</label>
                    <input type="password" id="accountPassword" style="width:100%;padding:0.8em;border-radius:6px;border:1px solid #444;background:#333;color:white;font-size:1em;">
                </div>
                <div id="accountLanguageField" style="margin-bottom:1em;">
                    <label style="display:block;margin-bottom:0.5em;color:#aaa;">언어 설정</label>
                    <select id="accountLanguage" style="width:100%;padding:0.8em;border-radius:6px;border:1px solid #444;background:#333;color:white;font-size:1em;">
                        <option value="">기본값 (변경 안함)</option>
                        <option value="ko-KR">한국어 (ko-KR)</option>
                        <option value="en-US">영어 (en-US)</option>
                        <option value="zh-CN">중국어 (zh-CN)</option>
                        <option value="mn-MN">몽골어 (mn-MN)</option>
                    </select>
                </div>
                <div style="display:flex;justify-content:flex-end;gap:1em;">
                    <button onclick="document.getElementById('accountModal').remove()" style="background:transparent;color:#aaa;border:1px solid #444;padding:0.6em 1.2em;border-radius:6px;cursor:pointer;">취소</button>
                    <button onclick="confirmAccountCommand()" style="background:#f59e0b;color:white;border:none;padding:0.6em 1.2em;border-radius:6px;cursor:pointer;font-weight:600;">실행</button>
                </div>
            </div>
        </div>
    `);
    updateAccountModalFields();
}

function updateAccountModalFields() {
    const action = document.getElementById('accountAction').value;
    const passwordField = document.getElementById('accountPasswordField');
    const languageField = document.getElementById('accountLanguageField');

    if (action === 'delete_user') {
        passwordField.style.display = 'none';
        languageField.style.display = 'none';
    } else if (action === 'change_password') {
        passwordField.style.display = 'block';
        languageField.style.display = 'none';
    } else {
        passwordField.style.display = 'block';
        languageField.style.display = 'block';
    }
}

function confirmAccountCommand() {
    const action = document.getElementById('accountAction').value;
    const username = document.getElementById('accountUsername').value.trim();
    const password = document.getElementById('accountPassword').value;
    const language = document.getElementById('accountLanguage').value;

    if (!username) { alert('사용자 이름을 입력하세요.'); return; }
    if (action !== 'delete_user' && !password) { alert('비밀번호를 입력하세요.'); return; }

    const commandData = { username };
    if (action !== 'delete_user') {
        if (action === 'change_password') {
            commandData.new_password = password;
        } else {
            commandData.password = password;
            commandData.language = language;
        }
    }

    document.getElementById('accountModal').remove();
    executeBulkCommand(action, commandData);
}

function showBulkPowerModal() {
    document.body.insertAdjacentHTML('beforeend', `
        <div id="powerModal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);z-index:2000;display:flex;align-items:center;justify-content:center;padding:2em;">
            <div style="background:#2a2a2a;border-radius:12px;padding:2em;max-width:400px;width:100%;color:white;text-align:center;">
                <h3 style="margin-top:0;margin-bottom:1.5em;">전원 관리</h3>
                <div style="display:flex;flex-direction:column;gap:1em;margin-bottom:1.5em;">
                    <button onclick="confirmPowerCommand('shutdown')" style="background:#dc2626;color:white;border:none;padding:1em;border-radius:8px;cursor:pointer;font-weight:600;font-size:1.1em;display:flex;align-items:center;justify-content:center;gap:0.5em;">
                        <i class="fas fa-power-off"></i> 시스템 종료
                    </button>
                    <button onclick="confirmPowerCommand('restart')" style="background:#f59e0b;color:white;border:none;padding:1em;border-radius:8px;cursor:pointer;font-weight:600;font-size:1.1em;display:flex;align-items:center;justify-content:center;gap:0.5em;">
                        <i class="fas fa-redo"></i> 시스템 재시작
                    </button>
                </div>
                <button onclick="document.getElementById('powerModal').remove()" style="background:transparent;color:#aaa;border:1px solid #444;padding:0.6em 1.2em;border-radius:6px;cursor:pointer;">취소</button>
            </div>
        </div>
    `);
}

function confirmPowerCommand(action) {
    const actionName = action === 'shutdown' ? '종료' : '재시작';
    if (!confirm(`선택된 ${selectedPCs.size}대의 PC를 ${actionName} 하시겠습니까?`)) return;
    document.getElementById('powerModal').remove();
    executeBulkCommand(action, {});
}

async function executeBulkCommand(commandType, commandData) {
    if (selectedPCs.size === 0) { alert('선택된 PC가 없습니다.'); return; }

    const pcIds = Array.from(selectedPCs);

    if (commandType !== 'shutdown' && commandType !== 'restart') {
        if (!confirm(`선택된 ${pcIds.length}대의 PC에 명령을 전송하시겠습니까?`)) return;
    }

    try {
        const response = await fetch('/api/pcs/bulk-command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pc_ids: pcIds, command_type: commandType, command_data: commandData })
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const result = await response.json();

        if (result.success > 0) {
            const commandIds = result.results.filter(r => r.status === 'success').map(r => r.command_id);
            if (commandIds.length > 0) {
                showCommandResultModal(commandIds, pcIds);
            } else {
                alert(`⚠️ 일부 명령 전송 실패\n\n성공: ${result.success}대\n실패: ${result.failed}대`);
            }
        } else {
            alert(`❌ 명령 전송 실패\n\n모든 PC에 명령 전송이 실패했습니다.\n\n${result.error || '알 수 없는 오류'}`);
        }
    } catch (error) {
        console.error('Bulk command error:', error);
        alert(`명령 전송 중 오류가 발생했습니다.\n\n${error.message}`);
    }
}

// ==================== 명령 결과 추적 ====================

let resultPollingInterval = null;

function showCommandResultModal(commandIds, pcIds) {
    if (resultPollingInterval) { clearInterval(resultPollingInterval); resultPollingInterval = null; }

    const modal = document.getElementById('commandResultModal');
    const resultList = document.getElementById('commandResultList');
    const statusDiv = document.getElementById('commandResultStatus');

    resultList.innerHTML = '';
    statusDiv.style.background = 'rgba(74, 158, 255, 0.1)';
    statusDiv.style.borderLeftColor = '#4a9eff';
    statusDiv.innerHTML = `
        <div style="display:flex;align-items:center;gap:1em;">
            <div class="spinner" id="loadingSpinner"></div>
            <div>
                <div style="color:white;font-weight:600;margin-bottom:0.3em;">명령 실행 중...</div>
                <div style="color:#aaa;font-size:0.9em;"><span id="completedCount">0</span> / <span id="totalCount">${commandIds.length}</span> 완료</div>
            </div>
        </div>
    `;

    const pcMap = {};
    allPCs.forEach(pc => { pcMap[pc.id] = pc; });

    commandIds.forEach((cmdId, index) => {
        const pc = pcMap[pcIds[index]] || {};
        const item = document.createElement('div');
        item.className = 'result-item pending';
        item.id = `result-${cmdId}`;
        item.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <strong style="color:white;">${pc.hostname || 'Unknown PC'}</strong>
                    <span style="color:#888;"> (${pc.seat_number || 'N/A'})</span>
                </div>
                <span class="status-badge" style="background:#f59e0b;color:white;padding:0.3em 0.8em;border-radius:4px;font-size:0.85em;">대기 중...</span>
            </div>
            <div class="result-content" style="display:none;"></div>
        `;
        resultList.appendChild(item);
    });

    modal.style.display = 'block';
    startResultPolling(commandIds);
}

async function startResultPolling(commandIds) {
    let completedCommands = new Set();

    const poll = async () => {
        try {
            const response = await fetch('/api/commands/results', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command_ids: commandIds })
            });

            if (!response.ok) { console.error('Failed to fetch results:', response.status); return; }

            const data = await response.json();
            data.results.forEach(cmd => {
                updateCommandResult(cmd);
                if (['completed', 'error', 'skipped'].includes(cmd.status)) completedCommands.add(cmd.id);
            });

            const completedCountEl = document.getElementById('completedCount');
            if (completedCountEl) completedCountEl.textContent = completedCommands.size;

            if (completedCommands.size === commandIds.length) {
                clearInterval(resultPollingInterval);
                resultPollingInterval = null;

                const spinner = document.getElementById('loadingSpinner');
                const statusDiv = document.getElementById('commandResultStatus');
                if (spinner) spinner.style.display = 'none';
                if (statusDiv) {
                    statusDiv.style.background = 'rgba(16, 185, 129, 0.1)';
                    statusDiv.style.borderLeftColor = '#10b981';
                    statusDiv.innerHTML = '<div style="color:#10b981;font-weight:600;"><i class="fas fa-check-circle"></i> 모든 명령 실행 완료!</div>';
                }
                clearSelection();
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    };

    await poll();
    resultPollingInterval = setInterval(poll, 2000);
}

function updateCommandResult(cmd) {
    const item = document.getElementById(`result-${cmd.id}`);
    if (!item) return;

    const statusMap = {
        'pending': { color: '#f59e0b', text: '대기 중...', cls: 'pending' },
        'executing': { color: '#4a9eff', text: '실행 중...', cls: 'executing' },
        'completed': { color: '#10b981', text: '완료', cls: 'completed' },
        'error': { color: '#dc2626', text: '오류', cls: 'error' },
        'skipped': { color: '#6366f1', text: '건너뜀', cls: 'skipped' }
    };

    const status = statusMap[cmd.status] || statusMap['pending'];
    item.className = `result-item ${status.cls}`;

    const badge = item.querySelector('.status-badge');
    if (badge) { badge.style.background = status.color; badge.textContent = status.text; }

    if (cmd.result || cmd.error_message) {
        const resultContent = item.querySelector('.result-content');
        if (resultContent) {
            resultContent.style.display = 'block';
            resultContent.textContent = cmd.result || cmd.error_message || '(결과 없음)';
        }
    }
}

function closeResultModal() {
    const modal = document.getElementById('commandResultModal');
    if (modal) modal.style.display = 'none';

    if (resultPollingInterval) { clearInterval(resultPollingInterval); resultPollingInterval = null; }
}

// ==================== 명령 초기화 기능 ====================

async function clearPendingCommands() {
    if (selectedPCs.size === 0) { await showPendingCommandsList(); return; }

    const pcIds = Array.from(selectedPCs);
    if (!confirm(`선택된 ${pcIds.length}대 PC의 대기 중인 명령을 모두 삭제하시겠습니까?`)) return;

    try {
        const response = await fetch('/api/pcs/commands/clear', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pc_ids: pcIds })
        });
        const result = await response.json();

        if (response.ok) {
            alert(`✅ 명령 삭제 완료\n\n총 ${result.total_deleted}개의 대기 명령이 삭제되었습니다.\n성공: ${result.success}대, 실패: ${result.failed}대`);
            clearSelection();
        } else {
            alert(`❌ 명령 삭제 실패: ${result.error || '알 수 없는 오류'}`);
        }
    } catch (error) {
        console.error('Clear commands error:', error);
        alert('명령 삭제 중 오류가 발생했습니다.');
    }
}

async function showPendingCommandsList() {
    try {
        const response = await fetch('/api/commands/pending');
        const data = await response.json();

        if (!response.ok) { alert('대기 명령 목록을 불러올 수 없습니다.'); return; }

        const panel = document.getElementById('pendingCommandsPanel');
        const list = document.getElementById('pendingCommandsList');
        const count = document.getElementById('pendingCommandCount');

        count.textContent = data.total;

        if (data.total === 0) {
            list.innerHTML = '<p style="color:#aaa;text-align:center;padding:2em;">대기 중인 명령이 없습니다.</p>';
        } else {
            list.innerHTML = data.commands.map(cmd => {
                const cmdData = JSON.parse(cmd.command_data || '{}');
                const cmdDataStr = Object.keys(cmdData).map(k => `${k}: ${cmdData[k]}`).join(', ');
                return `
                    <div style="background:rgba(255,255,255,0.05);padding:1em;margin-bottom:0.5em;border-radius:6px;border-left:4px solid #fbbf24;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <strong style="color:#fbbf24;">${cmd.hostname || 'Unknown'}</strong>
                                <span style="color:#888;"> (${cmd.seat_number || 'N/A'} - ${cmd.room_name || 'N/A'})</span>
                            </div>
                            <button onclick="clearSingleCommand(${cmd.pc_id}, ${cmd.command_id})" style="background:#dc2626;color:white;border:none;padding:0.4em 0.8em;border-radius:4px;cursor:pointer;font-size:0.85em;">삭제</button>
                        </div>
                        <div style="color:#ccc;font-size:0.9em;margin-top:0.5em;">
                            <span style="color:#4a9eff;">${cmd.command_type}</span> - ${cmdDataStr}
                        </div>
                        <div style="color:#888;font-size:0.8em;margin-top:0.3em;">생성: ${cmd.created_at} | 우선순위: ${cmd.priority}</div>
                    </div>
                `;
            }).join('');
        }

        panel.style.display = 'block';
    } catch (error) {
        console.error('Load pending commands error:', error);
        alert('대기 명령 목록을 불러오는 중 오류가 발생했습니다.');
    }
}

async function clearSingleCommand(pcId, commandId) {
    if (!confirm('이 명령을 삭제하시겠습니까?')) return;

    try {
        const response = await fetch(`/api/pc/${pcId}/commands/clear`, { method: 'DELETE' });
        const result = await response.json();

        if (response.ok) {
            alert(`✅ ${result.deleted_count}개의 명령이 삭제되었습니다.`);
            showPendingCommandsList();
        } else {
            alert(`❌ 삭제 실패: ${result.message || '알 수 없는 오류'}`);
        }
    } catch (error) {
        console.error('Clear single command error:', error);
        alert('명령 삭제 중 오류가 발생했습니다.');
    }
}

function closePendingPanel() {
    document.getElementById('pendingCommandsPanel').style.display = 'none';
}

// ==================== 중복 PC 관리 모달 ====================

async function showDuplicatePCsModal() {
    try {
        const response = await fetch('/api/pcs/duplicates');
        const data = await response.json();

        if (!response.ok) { alert('중복 PC 목록을 불러올 수 없습니다.'); return; }
        if (data.total_duplicate_groups === 0) { alert('중복된 PC가 없습니다.'); return; }

        let groupsHTML = '';
        data.duplicates.forEach(group => {
            const pcsHTML = group.pcs.map(pc => `
                <div style="background:rgba(0,0,0,0.3);padding:1em;border-radius:6px;display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="font-weight:600;">${pc.hostname}</div>
                        <small style="color:#aaa;">IP: ${pc.ip_address || 'N/A'} | MAC: ${pc.mac_address || 'N/A'} | Machine ID: ${pc.machine_id || 'N/A'}</small><br>
                        <small style="color:#888;">등록: ${pc.created_at || 'N/A'} | 배치: ${pc.room_name || '미배치'} ${pc.seat_number ? '(' + pc.seat_number + ')' : ''}</small>
                    </div>
                    <button onclick="deletePCFromDuplicateModal(${pc.id}, '${pc.hostname}')" style="background:#dc2626;color:white;border:none;padding:0.5em 1em;border-radius:6px;cursor:pointer;font-weight:600;white-space:nowrap;">🗑️ 삭제</button>
                </div>
            `).join('');

            groupsHTML += `
                <div style="background:rgba(255,255,255,0.05);padding:1em;margin-bottom:1em;border-radius:8px;border-left:4px solid #ff9800;">
                    <h4 style="margin-top:0;color:#ff9800;">${group.hostname} (${group.count}개)</h4>
                    <div style="display:flex;flex-direction:column;gap:0.5em;">${pcsHTML}</div>
                </div>
            `;
        });

        document.body.insertAdjacentHTML('beforeend', `
            <div id="duplicatePCsModal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);z-index:2000;display:flex;align-items:center;justify-content:center;padding:2em;">
                <div style="background:#2a2a2a;border-radius:12px;padding:2em;max-width:800px;max-height:80vh;overflow-y:auto;color:white;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5em;">
                        <h2 style="margin:0;">🔄 중복 PC 관리</h2>
                        <button onclick="document.getElementById('duplicatePCsModal').remove()" style="background:#dc2626;color:white;border:none;padding:0.5em 1em;border-radius:6px;cursor:pointer;font-weight:600;">닫기</button>
                    </div>
                    <div style="background:rgba(255,255,255,0.1);padding:1em;border-radius:8px;margin-bottom:1.5em;">
                        <p style="margin:0;color:#aaa;">총 <strong style="color:#ff9800;">${data.total_duplicate_groups}</strong>개의 중복 그룹이 있습니다.</p>
                    </div>
                    ${groupsHTML}
                </div>
            </div>
        `);
    } catch (error) {
        console.error('Load duplicates error:', error);
        alert('중복 PC 목록을 불러오는 중 오류가 발생했습니다.');
    }
}

async function deletePCFromDuplicateModal(pcId, hostname) {
    if (!confirm(`정말로 ${hostname} (ID: ${pcId})를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) return;

    try {
        const response = await fetch(`/api/pc/${pcId}`, { method: 'DELETE' });
        const result = await response.json();

        if (response.ok) {
            alert(`✅ ${hostname}이(가) 삭제되었습니다.`);
            document.getElementById('duplicatePCsModal').remove();
            location.reload();
        } else {
            alert(`❌ 삭제 실패: ${result.message || '알 수 없는 오류'}`);
        }
    } catch (error) {
        console.error('Delete PC error:', error);
        alert('PC 삭제 중 오류가 발생했습니다.');
    }
}
