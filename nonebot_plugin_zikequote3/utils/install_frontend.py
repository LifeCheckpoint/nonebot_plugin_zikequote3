from nonebot.log import logger
from pathlib import Path
import subprocess

def check_npm_command():
    """检查 npm 命令是否存在"""
    subprocess.run(['npm', '--version'], check=True, capture_output=True, shell=True)


def verify_installation() -> bool:
    """检查 node_modules 目录确认依赖是否安装成功"""
    return (_module_html_capture_root / "node_modules").is_dir()


def install_frontend_dependencies():
    """安装渲染截图前端依赖"""
    if verify_installation():
        logger.info("截图后端已存在，跳过安装")
        return
    
    logger.info("正在进行 ZikeQuote3 Node.js 依赖安装...")

    if not _module_html_capture_root.is_dir():
        raise FileNotFoundError(f"无法找到目录 '{_module_html_capture_root}'")

    try:
        check_npm_command()
    except subprocess.CalledProcessError | FileNotFoundError:
        raise EnvironmentError("找不到命令 'npm'，请检查是否安装 Node.js 并加入系统环境变量")
    except Exception as e:
        raise e

    try:
        subprocess.run(['npm', 'install'], check=True, cwd=_module_html_capture_root, shell=True)

        if verify_installation():
            logger.info("Node.js 依赖安装成功。")
            return
        else:
            raise RuntimeError("Node.js 依赖安装完成，但验证失败")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"运行 'npm install' 时发生错误: {e}")
        logger.error(f"退出代码: {e.returncode}. 安装失败.")
        raise e

    except Exception as e:
        raise e


if __name__ == "__main__":
    # 直接执行脚本时进行安装
    global _module_html_capture_root
    _module_html_capture_root = Path(__file__).parent.parent / "html_capture"
    try:
        install_frontend_dependencies()
    except Exception as e:
        print(e)
else:
    # 作为模块导入，使用配置好的路径
    from ..imports import _module_html_capture_root
