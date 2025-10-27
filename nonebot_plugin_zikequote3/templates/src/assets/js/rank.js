// 从 HTML 读取数据模块
const leaderboardData = JSON.parse(document.getElementById('leaderboard-data').textContent);

// 从 HTML 读取配置
const appConfig = JSON.parse(document.getElementById('app-config').textContent);
const maxAvatarThreshold = appConfig.maxAvatarThreshold;

// 从 HTML 读取统计数据数组并动态生成卡片
const statsData = JSON.parse(document.getElementById('stats-data').textContent);
function renderStats() {
    const container = document.getElementById('stats-container');
    container.innerHTML = '';  // 清空容器
    statsData.forEach(stat => {
        const card = document.createElement('div');
        card.className = 'stat-card';
        let formattedValue = stat.value;
        // 如果是数字，添加千位逗号格式化
        if (typeof stat.value === 'number') {
            formattedValue = stat.value.toLocaleString();
        }
        card.innerHTML = `
            <h3 class="stat-value">${formattedValue}</h3>
            <p class="stat-label">${stat.label}</p>
        `;
        container.appendChild(card);
    });
}

// 从 HTML 读取图表配置（包括真实 dates 和 seriesData）
const chartConfig = JSON.parse(document.getElementById('chart-config').textContent);
const topN = chartConfig.topN;
const dates = chartConfig.dates;
const seriesData = chartConfig.seriesData;

/**
 * 从图像URI计算平均颜色，使用随机采样128像素，并调整亮度到中等范围。
 * 支持URL或Base64数据URL输入。
 * @param {string} imageUri - 图像URI，例如"https://example.com/avatar.png" 或 "data:image/png;base64,iVBOR..."
 * @returns {Promise<string>} - 调整后的平均颜色，格式为RGB字符串，如"rgb(128, 128, 128)"
 */
async function calculateAverageColorFromUri(imageUri) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = 'Anonymous'; // 处理跨域图像
        img.src = imageUri;

        img.onload = () => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = img.width;
            canvas.height = img.height;

            // 绘制图像到Canvas
            ctx.drawImage(img, 0, 0);

            // 获取ImageData
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const { data, width, height } = imageData;
            const totalPixels = width * height;
            const sampleSize = Math.min(128, totalPixels); // 如果像素少于128，采样全部

            let rSum = 0, gSum = 0, bSum = 0;

            // 随机采样像素
            for (let i = 0; i < sampleSize; i++) {
                const x = Math.floor(Math.random() * width);
                const y = Math.floor(Math.random() * height);
                const pixelIndex = (y * width + x) * 4;

                rSum += data[pixelIndex];
                gSum += data[pixelIndex + 1];
                bSum += data[pixelIndex + 2];
            }

            // 计算平均RGB（基于采样数）
            let avgR = Math.round(rSum / sampleSize);
            let avgG = Math.round(gSum / sampleSize);
            let avgB = Math.round(bSum / sampleSize);

            // 计算感知亮度 (0.299R + 0.587G + 0.114B)
            let brightness = 0.299 * avgR + 0.587 * avgG + 0.114 * avgB;

            // 目标亮度128，中等范围80-176
            const targetBrightness = 128;
            const minBrightness = 80;
            const maxBrightness = 176;
            const factor = targetBrightness / Math.max(brightness, 1); // 避免除零

            // 调整RGB到目标亮度，但限制范围
            avgR = Math.max(0, Math.min(255, Math.round(avgR * factor)));
            avgG = Math.max(0, Math.min(255, Math.round(avgG * factor)));
            avgB = Math.max(0, Math.min(255, Math.round(avgB * factor)));

            // 重新计算亮度并微调如果超出范围
            brightness = 0.299 * avgR + 0.587 * avgG + 0.114 * avgB;
            if (brightness < minBrightness) {
                const adjust = (minBrightness - brightness) / Math.max(brightness, 1);
                avgR = Math.min(255, Math.round(avgR * (1 + adjust)));
                avgG = Math.min(255, Math.round(avgG * (1 + adjust)));
                avgB = Math.min(255, Math.round(avgB * (1 + adjust)));
            } else if (brightness > maxBrightness) {
                const adjust = maxBrightness / Math.max(brightness, 1);
                avgR = Math.max(0, Math.round(avgR * adjust));
                avgG = Math.max(0, Math.round(avgG * adjust));
                avgB = Math.max(0, Math.round(avgB * adjust));
            }

            resolve(`rgb(${avgR}, ${avgG}, ${avgB})`);
        };

        img.onerror = (error) => {
            reject(new Error(`Failed to load image: ${error}`));
        };
    });
}

// 排行榜渲染
function renderLeaderboard(containerId) {
    const container = document.getElementById(containerId);
    leaderboardData.forEach(user => {
        const item = document.createElement('li');
        item.className = 'leaderboard-item';
        if (user.rank > maxAvatarThreshold) {
            item.classList.add('no-avatar');
        }
        let avatarHtml = user.rank <= maxAvatarThreshold ? 
            `<img src="${user.avatar}" alt="${user.name}" class="avatar">` : '';
        item.innerHTML = `
            <span class="rank-number">#${user.rank}</span>
            ${avatarHtml}
            <div class="user-info">
                <span class="user-name">${user.name}</span>
                <span class="user-score">${user.score.toLocaleString()} 语录</span>
            </div>
        `;
        container.appendChild(item);
    });
}

// 初始化图表
async function initChart(chartId, topNParam = topN) {
    // 数据验证
    if (!dates || dates.length === 0) {
        console.error('Chart initialization failed: dates array is missing or empty in chart-config.');
        return;
    }
    if (!seriesData || seriesData.length < topNParam) {
        console.error(`Chart initialization failed: seriesData length (${seriesData ? seriesData.length : 0}) is less than topN (${topNParam}).`);
        return;
    }
    if (!seriesData.every((data, idx) => data.length === dates.length)) {
        console.error('Chart initialization failed: seriesData arrays do not match dates length.');
        return;
    }

    const chartDom = document.getElementById(chartId);
    const myChart = echarts.init(chartDom);
    const textSecondaryColor = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim();

    const topUsers = leaderboardData.slice(0, topNParam);
    const validSeriesData = seriesData.slice(0, topNParam);  // 取前 topN 系列

    // 异步计算每个 top 用户的平均颜色
    const userColors = await Promise.all(
        topUsers.map(async (user) => {
            try {
                return await calculateAverageColorFromUri(user.avatar);
            } catch (error) {
                console.warn(`Failed to calculate color for ${user.name}: ${error.message}`);
                return 'rgb(128, 128, 128)';  // Fallback 颜色
            }
        })
    );

    const series = topUsers.map((user, idx) => ({
        name: user.name,
        type: 'line',
        smooth: true,
        symbol: 'none',
        data: validSeriesData[idx],
        lineStyle: { width: 3, color: userColors[idx] },
        itemStyle: { color: userColors[idx] },
        label: { show: false }
    }));

    const allData = series.flatMap(s => s.data);
    const dataMin = Math.min(...allData);
    const dataMax = Math.max(...allData);
    const range = dataMax - dataMin;
    const yAxisMin = Math.floor((dataMin - range * 0.1) / 10) * 10;
    const yAxisMax = Math.ceil((dataMax + range * 0.1) / 10) * 10;

    const option = {
        animation: false,
        tooltip: { show: false },
        legend: {
            data: topUsers.map(u => u.name),
            bottom: 10,
            textStyle: { color: textSecondaryColor }
        },
        grid: {
            left: '40', 
            right: '130', 
            top: '40', 
            bottom: '80'
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: dates,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: textSecondaryColor }
        },
        yAxis: {
            type: 'value',
            min: yAxisMin,
            max: yAxisMax,
            splitLine: { lineStyle: { color: 'rgba(0, 0, 0, 0.08)' } },
            axisLabel: { color: textSecondaryColor }
        },
        series: series
    };

    myChart.setOption(option);

    // 在图表渲染完成后添加 graphic 元素
    myChart.on('rendered', function addGraphics() {
        // 移除监听器，避免重复添加
        myChart.off('rendered', addGraphics);

        const markers = createMarkers(myChart, validSeriesData, userColors);
        const chartWidth = chartDom.clientWidth;
        const bubbles = createBubbles(myChart, topUsers, validSeriesData, userColors, chartWidth);
        myChart.setOption({
            graphic: [...markers, ...bubbles]
        });
    });

    return { myChart, seriesData: validSeriesData, topUsers };
}

// 终点标志（使用用户平均颜色）
function createMarkers(myChart, seriesData, userColors) {
    const markers = [];
    seriesData.forEach((data, idx) => {
        const lastY = data[data.length - 1];
        const point = myChart.convertToPixel('series', [data.length - 1, lastY]);
        if (point && point[0] > 0 && point[1] > 0) {
            markers.push({
                type: 'circle',
                z: 110,
                shape: { cx: point[0], cy: point[1], r: 6 },
                style: {
                    fill: userColors[idx],
                    stroke: '#fff',
                    lineWidth: 2
                }
            });
        }
    });
    return markers;
}

// 圆角头像
function createBubbles(myChart, topUsers, seriesData, userColors, chartWidth) {
    const bubbles = [];
    // 收集所有point
    const pointsWithIdx = seriesData.map((data, idx) => {
        const lastY = data[data.length - 1];
        const point = myChart.convertToPixel('series', [data.length - 1, lastY]);
        return { idx, point };
    }).filter(p => p.point && p.point[0] > 0 && p.point[1] > 0);

    // 按 y 从上到下排序
    const sorted = pointsWithIdx.sort((a, b) => a.point[1] - b.point[1]);
    const initial_avatar_y = 0;
    const avatar_size = 60; // 宽度和高度
    const spacing = 15; // 终点标志到头像的间距
    const corner_radius = 12; // 圆角半径，轻微圆角

    sorted.forEach(({ idx, point }, rank) => {
        const user = topUsers[idx];
        const markerX = point[0];
        const markerY = point[1];
        let avatarX = markerX + spacing;
        let avatarY = Math.max(20, markerY - avatar_size / 2);

        // x边界检查：防止左溢出（最小20px）和右溢出（裕度20px）
        if (avatarX < 20) {
            avatarX = 20;
        }
        if (avatarX + avatar_size > chartWidth - 20) {
            avatarX = chartWidth - avatar_size - 20;
        }

        const bubbleZ = 105 - rank;

        const bubble = {
            type: 'group',
            z: bubbleZ,
            left: avatarX,
            top: avatarY,
            children: [
                // 平均颜色背景矩形
                {
                    type: 'rect',
                    z: 101,
                    shape: {
                        x: 0,
                        y: 0,
                        width: avatar_size,
                        height: avatar_size,
                        r: corner_radius
                    },
                    style: {
                        fill: userColors[idx]
                    }
                },
                // 圆角矩形裁剪的头像图像
                {
                    type: 'image',
                    style: {
                        image: user.avatar,
                        x: 0,
                        y: initial_avatar_y,
                        width: avatar_size,
                        height: avatar_size
                    },
                    clipPath: {
                        type: 'rect',
                        shape: {
                            x: 0,
                            y: 0,
                            width: avatar_size,
                            height: avatar_size,
                            r: corner_radius
                        }
                    },
                    z: 102
                }
            ]
        };
        bubbles.push(bubble);
    });

    // 反转顺序以便上层覆盖下层
    return bubbles.reverse();
}

// 初始化（先同步渲染统计和排行榜，再异步初始化图表）
renderStats();
renderLeaderboard('leaderboard');
(async () => {
    await initChart('main-chart', topN);
})();
