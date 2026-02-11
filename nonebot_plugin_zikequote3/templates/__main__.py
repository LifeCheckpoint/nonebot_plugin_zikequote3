"""
模板预览工具入口。

支持两种运行方式：

1. 直接运行（推荐，无需 NoneBot）：
   python nonebot_plugin_zikequote3/templates/__main__.py <template_name> [--open]

2. 模块运行（需要 NoneBot 环境）：
   python -m nonebot_plugin_zikequote3.templates <template_name> [--open]
"""
import sys
from pathlib import Path

# 当直接运行脚本时（非 -m 模式），需要手动设置包结构以支持相对导入
if __package__ is None or __package__ == "":
    _project_root = str(Path(__file__).resolve().parent.parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    # 创建父包的轻量 stub，避免触发 NoneBot 依赖
    import types

    _pkg_name = "nonebot_plugin_zikequote3"
    if _pkg_name not in sys.modules:
        _stub = types.ModuleType(_pkg_name)
        _stub.__path__ = [str(Path(__file__).resolve().parent.parent)]
        _stub.__package__ = _pkg_name
        sys.modules[_pkg_name] = _stub

from nonebot_plugin_zikequote3.templates.preview import main  # noqa: E402

main()
