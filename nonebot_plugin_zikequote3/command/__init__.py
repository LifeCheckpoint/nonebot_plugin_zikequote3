from .info_quote import *
from .modify_quote import *
from .read_quote import *
from .comand_definition import *

from ..utils.install_frontend import verify_installation, install_frontend_dependencies
driver = get_driver()
@driver.on_startup
async def f_startup():
    """
    启动后检查依赖
    """
    from ..imports import default_cfg

    if not default_cfg.general.enable_zikequote3 or not default_cfg.general.check_intergrity:
        return

    if verify_installation():
        return
    
    # 尝试安装依赖
    result = await asyncio.to_thread(install_frontend_dependencies)

    if result:
        logger.info("前端依赖安装完成")
    else:
        logger.error("前端依赖安装失败")