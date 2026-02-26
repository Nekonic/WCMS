// PC 상세 정보 모달 (base.html에서 추출)
// window.WCMS_IS_ADMIN 은 base.html에서 Jinja2로 설정됨

function openModal(pcId) {
    const modal = document.getElementById('pcModal');
    modal.classList.add('show');

    fetch(`/api/pc/${pcId}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('modalTitle').textContent = `${data.hostname} 상세 정보`;

            const body = document.getElementById('modalBody');

            // RAM 정보
            const ramTotal = data.ram_total || 0;
            const ramUsed = data.ram_used || 0;
            const ramFree = ramTotal - ramUsed;
            const ramPercent = ramTotal > 0 ? (ramUsed / ramTotal * 100) : 0;

            // 디스크 정보 파싱 및 포맷팅
            let diskDisplay = 'N/A';
            let diskChartHtml = '';
            if (data.disk_info_parsed && Object.keys(data.disk_info_parsed).length > 0) {
                try {
                    const diskParts = [];
                    const diskCharts = [];
                    let chartIndex = 0;

                    for (const [dev, info] of Object.entries(data.disk_info_parsed)) {
                        const total = info.total_gb || 0;
                        const used = info.used_gb || 0;
                        const free = info.free_gb || 0;
                        const percent = info.percent || 0;
                        diskParts.push(`${dev} ${used.toFixed(1)}/${total.toFixed(1)} GB (${percent.toFixed(0)}%)`);

                        const chartId = `modalDiskChart_${chartIndex}`;
                        diskCharts.push({ id: chartId, dev, used, free, percent, total });
                        chartIndex++;
                    }
                    diskDisplay = diskParts.join(', ');

                    diskChartHtml = '<div style="display: flex; gap: 20px; flex-wrap: wrap; margin-top: 15px;">';
                    diskCharts.forEach(chart => {
                        diskChartHtml += `
                            <div style="text-align: center; min-width: 150px;">
                                <div style="font-weight: bold; margin-bottom: 5px; color: #4a9eff;">${chart.dev}</div>
                                <canvas id="${chart.id}" width="120" height="120"></canvas>
                                <div style="font-size: 0.85em; color: #999; margin-top: 5px;">
                                    ${chart.used.toFixed(1)}/${chart.total.toFixed(1)} GB
                                </div>
                            </div>
                        `;
                    });
                    diskChartHtml += '</div>';

                    setTimeout(() => {
                        diskCharts.forEach(chart => {
                            const ctx = document.getElementById(chart.id);
                            if (ctx && typeof Chart !== 'undefined') {
                                new Chart(ctx, {
                                    type: 'doughnut',
                                    data: {
                                        labels: ['사용', '여유'],
                                        datasets: [{
                                            data: [chart.used, chart.free],
                                            backgroundColor: [
                                                chart.percent > 90 ? '#ef4444' : chart.percent > 75 ? '#f59e0b' : '#10b981',
                                                '#374151'
                                            ],
                                            borderColor: ['#1a1a1a', '#1a1a1a'],
                                            borderWidth: 2
                                        }]
                                    },
                                    options: {
                                        responsive: false,
                                        plugins: {
                                            legend: { display: false },
                                            tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${ctx.parsed.toFixed(1)} GB` } }
                                        }
                                    }
                                });
                            }
                        });
                    }, 100);
                } catch(e) {
                    console.error('Disk info parsing error:', e);
                    diskDisplay = 'N/A';
                }
            }

            const ramChartHtml = `
                <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-top: 15px; margin-bottom: 15px;">
                    <div style="text-align: center; min-width: 150px;">
                        <div style="font-weight: bold; margin-bottom: 5px; color: #4a9eff;">RAM</div>
                        <canvas id="modalRamChart" width="120" height="120"></canvas>
                        <div style="font-size: 0.85em; color: #999; margin-top: 5px;">
                            ${ramUsed.toFixed(1)}/${ramTotal.toFixed(1)} GB (${ramPercent.toFixed(0)}%)
                        </div>
                    </div>
                </div>
            `;

            body.innerHTML = `
                <div class="detail-row"><span class="detail-label">실습실:</span><span class="detail-value">${data.room_name || '미배치'}</span></div>
                <div class="detail-row"><span class="detail-label">좌석:</span><span class="detail-value">${data.seat_number || 'N/A'}</span></div>
                <div class="detail-row"><span class="detail-label">상태:</span><span class="detail-value">${data.is_online ? '온라인' : '오프라인'}</span></div>
                <div class="detail-row"><span class="detail-label">CPU:</span><span class="detail-value">${data.cpu_model || 'N/A'}</span></div>
                <div class="detail-row"><span class="detail-label">RAM:</span><span class="detail-value">${data.ram_total || 0} GB</span></div>
                ${ramChartHtml}
                <div class="detail-row"><span class="detail-label">디스크:</span><span class="detail-value">${diskDisplay}</span></div>
                ${diskChartHtml}
                <div class="detail-row"><span class="detail-label">OS:</span><span class="detail-value">${data.os_edition || 'N/A'}</span></div>
                <div class="detail-row"><span class="detail-label">IP:</span><span class="detail-value">${data.ip_address || 'N/A'}</span></div>
                <div class="detail-row"><span class="detail-label">MAC:</span><span class="detail-value">${data.mac_address || 'N/A'}</span></div>
            `;

            setTimeout(() => {
                const ctx = document.getElementById('modalRamChart');
                if (ctx && typeof Chart !== 'undefined') {
                    new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: ['사용', '여유'],
                            datasets: [{
                                data: [ramUsed, ramFree],
                                backgroundColor: [
                                    ramPercent > 90 ? '#ef4444' : ramPercent > 75 ? '#f59e0b' : '#10b981',
                                    '#374151'
                                ],
                                borderColor: ['#1a1a1a', '#1a1a1a'],
                                borderWidth: 2
                            }]
                        },
                        options: {
                            responsive: false,
                            plugins: {
                                legend: { display: false },
                                tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${ctx.parsed.toFixed(1)} GB` } }
                            }
                        }
                    });
                }
            }, 100);

            const footer = document.getElementById('modalFooter');
            if (window.WCMS_IS_ADMIN) {
                footer.innerHTML = `
                    <a href="/pc/${pcId}/history" class="btn btn-info">기록 보기</a>
                    <button class="btn btn-danger" onclick="shutdownPC(${pcId})">종료</button>
                    <button class="btn btn-warning" onclick="rebootPC(${pcId})">재시작</button>
                `;
            } else {
                footer.innerHTML = '<p style="color: #666;">제어 기능은 로그인 후 사용 가능합니다.</p>';
            }
        })
        .catch(err => {
            console.error('Error:', err);
            document.getElementById('modalBody').innerHTML = '<p style="color: #f00;">데이터를 불러올 수 없습니다.</p>';
        });
}

function closeModal() {
    document.getElementById('pcModal').classList.remove('show');
}

function shutdownPC(pcId) {
    if (!confirm('정말 이 PC를 종료하시겠습니까?')) return;
    fetch(`/api/pc/${pcId}/shutdown`, { method: 'POST' })
        .then(res => res.json())
        .then(data => { alert(data.message || '종료 명령 전송 완료'); closeModal(); })
        .catch(err => alert('오류 발생: ' + err));
}

function rebootPC(pcId) {
    if (!confirm('정말 이 PC를 재시작하시겠습니까?')) return;
    fetch(`/api/pc/${pcId}/reboot`, { method: 'POST' })
        .then(res => res.json())
        .then(data => { alert(data.message || '재시작 명령 전송 완료'); closeModal(); })
        .catch(err => alert('오류 발생: ' + err));
}

window.addEventListener('click', (event) => {
    const modal = document.getElementById('pcModal');
    if (event.target === modal) closeModal();
});
