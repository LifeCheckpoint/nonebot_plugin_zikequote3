from .cmds import *

from ..utils.install_frontend import verify_installation, install_frontend_dependencies
driver = get_driver()
@driver.on_startup
async def f_startup():
    """
    启动后检查依赖
    """
    from ..imports import default_cfg

    if not default_cfg.general.check_intergrity:
        return

    if verify_installation():
        return
    
    # 尝试安装依赖
    await asyncio.to_thread(install_frontend_dependencies)
