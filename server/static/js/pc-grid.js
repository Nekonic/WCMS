// PC 그리드 - 선택 모드 및 좌석 배치 렌더링 (index.html에서 추출)
// 의존 전역변수: room, allPCs, selectedPCs, selectionMode, isDragging, dragStartPos
// (index.html 인라인 스크립트에서 Jinja2로 초기화됨)

// PC 상세 모달 대신 history 페이지로 이동 (index.html 전용 동작)
function openModal(pcId) {
    window.location.href = `/pc/${pcId}`;
}

// 선택 모드 토글
function toggleSelectionMode() {
    selectionMode = !selectionMode;
    const btn = document.getElementById('selectionModeBtn');
    const cells = document.querySelectorAll('.seat-cell.occupied');

    if (selectionMode) {
        btn.style.background = '#dc2626';
        btn.textContent = '✖ 선택 모드 종료';
        cells.forEach(cell => cell.classList.add('selection-mode'));
    } else {
        btn.style.background = '#6366f1';
        btn.textContent = '📋 선택 모드';
        cells.forEach(cell => cell.classList.remove('selection-mode'));
        clearSelection();
    }
}

// PC 선택/해제
function togglePCSelection(pcId, event) {
    if (event) event.stopPropagation();
    if (selectedPCs.has(pcId)) {
        selectedPCs.delete(pcId);
    } else {
        selectedPCs.add(pcId);
    }
    updateSelectionUI();
}

// 전체 온라인 PC 선택
function selectAllOnlinePCs() {
    if (!selectionMode) toggleSelectionMode();
    allPCs.forEach(pc => { if (pc.is_online) selectedPCs.add(pc.id); });
    updateSelectionUI();
}

// 선택 해제
function clearSelection() {
    selectedPCs.clear();
    updateSelectionUI();
}

// 선택 UI 업데이트
function updateSelectionUI() {
    const panel = document.getElementById('selectedPCsPanel');
    const count = document.getElementById('selectedCount');
    const list = document.getElementById('selectedPCsList');

    count.textContent = selectedPCs.size;

    if (selectedPCs.size > 0) {
        panel.style.display = 'block';
        list.innerHTML = '';
        selectedPCs.forEach(pcId => {
            const pc = allPCs.find(p => p.id === pcId);
            if (pc) {
                const tag = document.createElement('div');
                tag.className = 'selected-pc-tag';
                tag.innerHTML = `
                    <span>${pc.seat_number || pc.hostname}</span>
                    <button class="remove-btn" onclick="togglePCSelection(${pcId}, event)">×</button>
                `;
                list.appendChild(tag);
            }
        });
    } else {
        panel.style.display = 'none';
    }

    document.querySelectorAll('.seat-cell.occupied').forEach(cell => {
        const pcId = parseInt(cell.dataset.pcId);
        const checkbox = cell.querySelector('.seat-checkbox');
        if (checkbox) {
            if (selectedPCs.has(pcId)) {
                cell.classList.add('selected');
                checkbox.classList.add('checked');
            } else {
                cell.classList.remove('selected');
                checkbox.classList.remove('checked');
            }
        }
    });
}

// 드래그 선택
function handleMouseDown(pcId, row, col) {
    if (!selectionMode) return;
    isDragging = true;
    dragStartPos = { row, col };
}

function handleMouseOver(pcId, row, col) {
    if (!selectionMode || !isDragging || !dragStartPos) return;

    const minRow = Math.min(dragStartPos.row, row);
    const maxRow = Math.max(dragStartPos.row, row);
    const minCol = Math.min(dragStartPos.col, col);
    const maxCol = Math.max(dragStartPos.col, col);

    document.querySelectorAll('.seat-cell.occupied').forEach(cell => {
        const cellRow = parseInt(cell.dataset.row);
        const cellCol = parseInt(cell.dataset.col);
        const cellPcId = parseInt(cell.dataset.pcId);

        if (cellRow >= minRow && cellRow <= maxRow && cellCol >= minCol && cellCol <= maxCol) {
            selectedPCs.add(cellPcId);
        }
    });

    updateSelectionUI();
}

function handleMouseUp() {
    isDragging = false;
    dragStartPos = null;
}

document.addEventListener('mouseup', handleMouseUp);

// 좌석 배치 렌더링
function renderLayout() {
    fetch(`/api/layout/map/${room}`)
        .then(res => res.json())
        .then(data => {
            const grid = document.getElementById('layoutGrid');
            grid.style.gridTemplateColumns = `repeat(${data.cols}, 1fr)`;
            grid.innerHTML = '';

            const pcMap = {};
            allPCs.forEach(pc => { pcMap[pc.id] = pc; });

            for (let row = 0; row < data.rows; row++) {
                for (let col = 0; col < data.cols; col++) {
                    const seat = data.seats.find(s => s.row === row && s.col === col);
                    const pc = seat && seat.pc_id ? pcMap[seat.pc_id] : null;

                    const div = document.createElement('div');
                    div.className = `seat-cell ${pc ? 'occupied' : 'empty'}`;

                    if (pc) {
                        div.dataset.pcId = pc.id;
                        div.dataset.row = row;
                        div.dataset.col = col;

                        const color = !pc.is_online ? '#555' :
                                     (pc.cpu_usage && pc.cpu_usage > 90) ? '#dc2626' :
                                     (pc.cpu_usage && pc.cpu_usage > 75) ? '#f59e0b' : '#10b981';

                        div.style.background = color;
                        div.style.borderColor = color;

                        div.innerHTML = `
                            <div class="seat-checkbox"></div>
                            <div style="font-weight: bold; color: white; font-size: 0.9em;">${pc.seat_number}</div>
                            <div style="font-size: 0.75em; color: #ddd;">${pc.hostname}</div>
                            <div style="font-size: 0.65em; color: #ccc;">
                                ${!pc.is_online ? '오프라인' :
                                  pc.cpu_usage ? `CPU: ${Math.round(pc.cpu_usage)}%` : '온라인'}
                            </div>
                        `;

                        div.onclick = (e) => {
                            if (selectionMode) {
                                togglePCSelection(pc.id, e);
                            } else {
                                openModal(pc.id);
                            }
                        };

                        div.onmousedown = () => handleMouseDown(pc.id, row, col);
                        div.onmouseover = () => handleMouseOver(pc.id, row, col);
                    } else {
                        div.innerHTML = '<div style="color: #666; font-size: 0.8em;">빈 칸</div>';
                    }

                    grid.appendChild(div);
                }
            }
        })
        .catch(error => {
            console.error('Error loading layout:', error);
            alert('배치를 불러올 수 없습니다.');
        });
}

renderLayout();
