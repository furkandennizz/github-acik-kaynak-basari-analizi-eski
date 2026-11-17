/**
 * GitHub MCDM Dashboard - Grafik ve Tablo Modülü
 * 
 * Bu dosya dashboard'daki tüm grafikleri ve tabloları oluşturur.
 * Chart.js kütüphanesi kullanılmaktadır.
 */

// ===========================================
// YARDIMCI FONKSİYONLAR
// ===========================================

/**
 * Sayıyı binlik ayraçlı formata çevirir
 */
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return num.toLocaleString('tr-TR');
}

/**
 * Proje adını kısaltır
 */
function shortenName(name, maxLength = 15) {
    const shortName = name.split('/')[1] || name;
    return shortName.length > maxLength 
        ? shortName.substring(0, maxLength) + '...' 
        : shortName;
}

/**
 * Gradient renk oluşturur
 */
function createGradient(ctx, colorStart, colorEnd) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, colorStart);
    gradient.addColorStop(1, colorEnd);
    return gradient;
}

// ===========================================
// TABLO OLUŞTURMA
// ===========================================

function createTable() {
    const tableBody = document.getElementById('tableBody');
    
    if (!tableBody) {
        console.error('❌ tableBody elementi bulunamadı!');
        return;
    }
    
    if (!top20Data || !Array.isArray(top20Data)) {
        console.error('❌ top20Data verisi geçersiz!');
        return;
    }
    
    // Tabloyu temizle
    tableBody.innerHTML = '';
    
    // Verileri ekle
    top20Data.forEach((project, index) => {
        const row = document.createElement('tr');
        
        // Sıralama rengini belirle (ilk 3 için özel)
        let rankClass = '';
        let rankIcon = '';
        if (index === 0) {
            rankClass = 'style="color: #FFD700; font-size: 1.3em;"'; // Altın
            rankIcon = '🥇';
        } else if (index === 1) {
            rankClass = 'style="color: #C0C0C0; font-size: 1.2em;"'; // Gümüş
            rankIcon = '🥈';
        } else if (index === 2) {
            rankClass = 'style="color: #CD7F32; font-size: 1.2em;"'; // Bronz
            rankIcon = '🥉';
        }
        
        row.innerHTML = `
            <td ${rankClass}><strong>${rankIcon} ${project.rank}</strong></td>
            <td>
                <a href="https://github.com/${project.name}" target="_blank" 
                   style="color: #667eea; text-decoration: none;">
                    ${project.name}
                </a>
            </td>
            <td>
                <span style="color: #48bb78; font-weight: bold;">
                    ${project.score.toFixed(2)}%
                </span>
            </td>
            <td>⭐ ${formatNumber(project.stars)}</td>
            <td>🔄 ${formatNumber(project.forks)}</td>
            <td>👥 ${formatNumber(project.contributors || 0)}</td>
        `;
        
        tableBody.appendChild(row);
    });
    
    console.log('✅ Tablo oluşturuldu:', top20Data.length, 'proje');
}

// ===========================================
// AĞIRLIK GRAFİĞİ
// ===========================================

function createWeightsChart() {
    const ctx = document.getElementById('weightsChart');
    
    if (!ctx) {
        console.error('❌ weightsChart canvas bulunamadı!');
        return;
    }
    
    if (!weightsData || !criteriaLabels) {
        console.error('❌ weightsData veya criteriaLabels eksik!');
        return;
    }
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: criteriaLabels,
            datasets: [
                {
                    label: 'Klasik AHP',
                    data: weightsData.classic,
                    backgroundColor: 'rgba(52, 152, 219, 0.8)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 2,
                    borderRadius: 5
                },
                {
                    label: 'Fuzzy AHP',
                    data: weightsData.fuzzy,
                    backgroundColor: 'rgba(231, 76, 60, 0.8)',
                    borderColor: 'rgba(231, 76, 60, 1)',
                    borderWidth: 2,
                    borderRadius: 5
                },
                {
                    label: 'Entropy',
                    data: weightsData.entropy,
                    backgroundColor: 'rgba(46, 204, 113, 0.8)',
                    borderColor: 'rgba(46, 204, 113, 1)',
                    borderWidth: 2,
                    borderRadius: 5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            size: 12,
                            weight: 'bold'
                        },
                        padding: 20
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.raw.toFixed(2) + '%';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 55,
                    title: {
                        display: true,
                        text: 'Ağırlık (%)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45,
                        font: {
                            size: 11
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
    
    console.log('✅ Ağırlık grafiği oluşturuldu');
}

// ===========================================
// TOP 10 PROJE GRAFİĞİ
// ===========================================

function createProjectsChart() {
    const ctx = document.getElementById('projectsChart');
    
    if (!ctx) {
        console.error('❌ projectsChart canvas bulunamadı!');
        return;
    }
    
    if (!top20Data) {
        console.error('❌ top20Data eksik!');
        return;
    }
    
    const top10 = top20Data.slice(0, 10);
    
    // Renk paleti (gradient efekti)
    const colors = [
        'rgba(102, 126, 234, 0.9)',  // 1. - Mor
        'rgba(118, 75, 162, 0.85)',   // 2. - Koyu Mor
        'rgba(237, 100, 166, 0.8)',   // 3. - Pembe
        'rgba(246, 211, 101, 0.8)',   // 4. - Sarı
        'rgba(253, 160, 133, 0.8)',   // 5. - Turuncu
        'rgba(72, 187, 120, 0.8)',    // 6. - Yeşil
        'rgba(66, 153, 225, 0.8)',    // 7. - Mavi
        'rgba(159, 122, 234, 0.8)',   // 8. - Açık Mor
        'rgba(237, 137, 54, 0.8)',    // 9. - Koyu Turuncu
        'rgba(160, 174, 192, 0.8)'    // 10. - Gri
    ];
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top10.map(p => shortenName(p.name, 18)),
            datasets: [{
                label: 'TOPSIS Skoru',
                data: top10.map(p => p.score),
                backgroundColor: colors,
                borderColor: colors.map(c => c.replace('0.8', '1').replace('0.85', '1').replace('0.9', '1')),
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const index = context[0].dataIndex;
                            return top10[index].name;
                        },
                        label: function(context) {
                            return 'Skor: ' + context.raw.toFixed(2) + '%';
                        },
                        afterLabel: function(context) {
                            const index = context.dataIndex;
                            const project = top10[index];
                            return [
                                '⭐ Stars: ' + formatNumber(project.stars),
                                '🔄 Forks: ' + formatNumber(project.forks)
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'TOPSIS Skoru (%)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    ticks: {
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
    
    console.log('✅ Top 10 proje grafiği oluşturuldu');
}

// ===========================================
// KORELASYON HEATMAP
// ===========================================

function createCorrelationChart() {
    const ctx = document.getElementById('correlationChart');
    
    if (!ctx) {
        console.error('❌ correlationChart canvas bulunamadı!');
        return;
    }
    
    // corrMatrix yoksa varsayılan değer kullan
    const matrix = (typeof corrMatrix !== 'undefined' && corrMatrix) 
        ? corrMatrix 
        : [
            [1.000, 0.994, 0.898],
            [0.994, 1.000, 0.895],
            [0.898, 0.895, 1.000]
        ];
    
    const methods = ['TOPSIS\n(Klasik)', 'TOPSIS\n(Fuzzy)', 'VIKOR'];
    
    // Heatmap için veri hazırla
    const data = [];
    const backgroundColors = [];
    const labels = [];
    
    for (let i = 0; i < 3; i++) {
        for (let j = 0; j < 3; j++) {
            data.push({
                x: methods[j],
                y: methods[i],
                v: matrix[i][j]
            });
            
            // Renk hesapla (yeşil tonları)
            const value = matrix[i][j];
            const intensity = Math.floor((value - 0.8) * 500); // 0.8-1.0 arası
            backgroundColors.push(`rgba(72, 187, 120, ${0.3 + value * 0.7})`);
        }
    }
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: methods,
            datasets: methods.map((method, i) => ({
                label: method.replace('\n', ' '),
                data: matrix[i],
                backgroundColor: matrix[i].map(v => {
                    if (v === 1) return 'rgba(102, 126, 234, 0.9)';
                    if (v > 0.95) return 'rgba(72, 187, 120, 0.8)';
                    if (v > 0.9) return 'rgba(246, 211, 101, 0.8)';
                    return 'rgba(237, 100, 166, 0.8)';
                }),
                borderWidth: 1,
                borderRadius: 5
            }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: { size: 11 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': τ = ' + context.raw.toFixed(3);
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Kendall Tau Korelasyon Değerleri',
                    font: { size: 14 }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    min: 0.85,
                    max: 1.02,
                    title: {
                        display: true,
                        text: 'Korelasyon (τ)'
                    }
                }
            }
        }
    });
    
    console.log('✅ Korelasyon grafiği oluşturuldu');
}

// ===========================================
// ANA BAŞLATICI
// ===========================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Dashboard yükleniyor...');
    
    try {
        // Tablo
        createTable();
        
        // Grafikler
        createWeightsChart();
        createProjectsChart();
        createCorrelationChart();
        
        console.log('✅ Dashboard başarıyla yüklendi!');
        
    } catch (error) {
        console.error('❌ Dashboard yükleme hatası:', error);
    }
});

// ===========================================
// EK: VERİ YENİLEME
// ===========================================

function refreshData() {
    fetch('/api/refresh')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('✅ Veriler yenilendi! Sayfa yenilenecek...');
                location.reload();
            } else {
                alert('❌ Hata: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Refresh hatası:', error);
            alert('❌ Bağlantı hatası!');
        });
}