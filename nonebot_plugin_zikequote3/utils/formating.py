"""
格式化工具。

提供颜色调色板生成等格式化辅助功能。
"""

import random
import colorsys
from typing import List


def generate_color_palette(num_colors: int) -> List[str]:
    """
    生成同色系的十六进制颜色调色板。

    基于随机基准色相，在 ±15° 范围内波动生成一组视觉协调的颜色。

    :param num_colors: 需要生成的颜色数量
    :type num_colors: int
    :returns: 十六进制颜色字符串列表，如 ``["#3A7BC8", "#2E6DB5"]``
    :rtype: List[str]
    """
    # 随机选择一个基准色相（0-360度）
    base_hue = random.uniform(0, 360)
    
    colors = []
    for _ in range(num_colors):
        # 允许色相在±15度范围内波动（保持同色系）
        hue = (base_hue + random.uniform(-15, 15)) % 360
        # 饱和度控制（中等偏高，0.65-0.85）
        saturation = random.uniform(0.65, 0.85)
        # 亮度控制（避免过亮过暗，0.25-0.65）
        lightness = random.uniform(0.25, 0.65)
        # 将HSL转换为RGB（使用colorsys的hls转换）
        r, g, b = colorsys.hls_to_rgb(hue/360, lightness, saturation)
        # 转换为0-255整数值并确保范围正确
        r, g, b = [max(0, min(int(x * 255), 255)) for x in (r, g, b)]
        # 格式化为十六进制字符串
        hex_color = "#{:02X}{:02X}{:02X}".format(r, g, b)
        colors.append(hex_color)

    return colors
