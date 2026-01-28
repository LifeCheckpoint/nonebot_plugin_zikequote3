from pathlib import Path
import nonebot_plugin_localstore as store

class PluginPath:
    """
    插件模块路径
    """
    plugin_root = Path(__file__).parent
    module_command_root = plugin_root / "command"
    module_database_root = plugin_root / "database"
    module_html_capture_root = plugin_root / "html_capture"
    module_llm_services_root = plugin_root / "llm_services"
    module_msgtexts_root = plugin_root / "msgtexts"
    module_resources_root = plugin_root / "resources"
    module_services_root = plugin_root / "services"
    module_templates_root = plugin_root / "templates"
    module_templates_htmls_root = module_templates_root / "src" / "htmls"
    module_templates_css_root = module_templates_root / "src" / "assets" / "css"
    module_templates_js_root = module_templates_root / "src" / "assets" / "js"
    module_utils_root = plugin_root / "utils"

    data_db_path = store.get_data_dir("ZikeQuote3") / "zikequote3.db"
    data_image_root = store.get_data_dir("ZikeQuote3") / "quote_images"
    data_cache_path = store.get_cache_dir("ZikeQuote3")
