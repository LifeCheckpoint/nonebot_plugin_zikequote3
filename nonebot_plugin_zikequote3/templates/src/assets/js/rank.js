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
 * 从图像URI计算感知平均色，使用ColorThief提取主导色。
 * 支持URL或Base64数据URL输入。假设图像不透明。
 * @param {string} imageUri - 图像URI
 * @param {number} [quality=10] - ColorThief采样质量，值越小精度越高但计算越慢
 * @returns {Promise<string>} - 主导平均颜色，RGB字符串
 */
async function calculateAverageColorFromUri(imageUri, quality = 10) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = 'Anonymous';
        img.src = imageUri;

        img.onload = () => {
            const colorThief = new ColorThief();
            const dominantColor = colorThief.getColor(img, quality); // 返回 [R, G, B]
            
            if (!dominantColor) {
                resolve('rgb(150, 150, 150)'); // 回退到中性灰
                return;
            }

            const [avgR, avgG, avgB] = dominantColor;
            resolve(`rgb(${avgR}, ${avgG}, ${avgB})`);
        };

        img.onerror = (error) => reject(new Error(`Failed to load image: ${error}`));
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
            right: '40',  // 减少右边距，为HTML面板腾空间
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

    // 在图表渲染完成后添加HTML终点组件
    myChart.on('rendered', function addEndpoints() {
        // 移除监听器，避免重复添加
        myChart.off('rendered', addEndpoints);

        createHTMLEndpoints(myChart, validSeriesData, topUsers, userColors);
    });

    // 处理窗口大小变化，重新定位HTML组件
    window.addEventListener('resize', () => {
        if (myChart) {
            myChart.resize();
            createHTMLEndpoints(myChart, validSeriesData, topUsers, userColors);
        }
    });

    return { myChart, seriesData: validSeriesData, topUsers };
}

// 创建HTML终点标记和卡片组件
function createHTMLEndpoints(myChart, seriesData, topUsers, userColors) {
    const panel = document.getElementById('endpoints-panel');
    panel.innerHTML = '';

    // 收集所有Y像素位置
    const pointsWithIdx = seriesData.map((data, idx) => {
        const lastY = data[data.length - 1];
        const point = myChart.convertToPixel('series', [data.length - 1, lastY]);
        return { idx, point };
    }).filter(p => p.point && p.point[0] > 0 && p.point[1] > 0);

    // 按 Y 从上到下排序
    const sorted = pointsWithIdx.sort((a, b) => a.point[1] - b.point[1]);

    sorted.forEach(({ idx, point }, rank) => {
        const user = topUsers[idx];
        const markerY = point[1];
        // 卡片的垂直居中（每个卡片高度为64px，头像垂直居中）
        const cardY = markerY - 32;

        const item = document.createElement('div');
        item.className = 'endpoint-item';
        item.style.top = `${cardY}px`;

        item.innerHTML = `
            <div class="endpoint-marker" style="background-color: ${userColors[idx]}"></div>
            <div class="endpoint-card" style="background-color: ${userColors[idx]}; border-color: ${userColors[idx]}20;">
                <div class="endpoint-pointer"></div>
                <div class="endpoint-avatar-bg" style="background-color: ${userColors[idx]};">
                    <img src="${user.avatar}" alt="${user.name}" class="endpoint-avatar">
                </div>
                <hr class="endpoint-divider">
                <div class="endpoint-details">
                    <p class="endpoint-name">${user.name}</p>
                    <p class="endpoint-score">${user.score.toLocaleString()} 语录</p>
                </div>
            </div>
        `;
        panel.appendChild(item);
    });
}

// 初始化（先同步渲染统计和排行榜，再异步初始化图表）
renderStats();
renderLeaderboard('leaderboard');
(async () => {
    await initChart('main-chart', topN);
})();
