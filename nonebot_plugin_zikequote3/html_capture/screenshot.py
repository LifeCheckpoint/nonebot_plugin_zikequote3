"""
对网页进行截图
"""
from nonebot import logger
from pathlib import Path
from typing import Tuple, Union
import asyncio
import subprocess

NODE_SCRIPT_PATH = Path(__file__).parent / 'screenshot.js'

async def async_generate_screenshot(
    html_file: Path,
    save_name: Path,
    width: int = 1000,
    height: int = 800,
    device_scale_factor: float = 2.0
) -> Tuple[int, str, str]:
    """
    异步生成网页截图。

    Args:
        html_file (str): HTML 文件绝对路径。
        save_name (str): 截图保存文件绝对路径。
        width (int): 视口宽度。
        height (int): 视口高度。
        device_scale_factor (float): 设备缩放因子。

    Returns:
        tuple: 包含 (返回码, 标准输出, 标准错误) 的元组。
               返回码是 Node.js 进程的退出码。
               标准输出和标准错误是捕获到的字符串。
    """

    command = [
        'node',
        str(NODE_SCRIPT_PATH),
        str(save_name.absolute()),
        str(html_file.absolute()),
        str(width),
        str(height),
        str(device_scale_factor)
    ]

    try:
        # 异步创建子进程
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # 异步等待进程完成并读取输出
        stdout, stderr = await process.communicate()

        stdout_str = stdout.decode('utf-8').strip()
        stderr_str = stderr.decode('utf-8').strip()

        if process.returncode == 0:
            logger.success("截图生成成功")
        elif process.returncode is None:
            logger.error("截图进程未正确启动")
            raise RuntimeError("截图进程未正确启动")
        else:
            logger.error(f"截图生成失败 (返回码: {process.returncode})")
            if stderr_str:
                logger.error("Node.js 错误:", stderr_str)
            raise RuntimeError(f"截图生成失败，返回码: {process.returncode}")

        return process.returncode, stdout_str, stderr_str

    except FileNotFoundError:
        logger.error("截图错误: 未找到 node 或 screenshot.js。请确保它们在系统路径中或脚本路径正确。")
        raise FileNotFoundError("未找到 node 或 screenshot.js")
    
    except Exception as e:
        logger.error(f"截图错误: {e}")
        raise e
