from ...imports import *
from ...imports import _cfg_toml, _default_cfg_toml

def s_get_setting_html(group_id: int) -> str:
    """获取群组配置"""
    from ...templates.schema.code_frame import render_code_frame, TemplateCodeFrameData

    is_default = _cfg_toml.get(group_id, None) is None
    
    with service_exception("获取语录配置预览 HTML"):
        return render_code_frame(
            TemplateCodeFrameData(
                title="语录配置预览",
                subtitle=f"群聊 {group_id}" + ("（默认配置）" if is_default else ""),
                language="toml",
                code=tomlkit.dumps(_cfg_toml.get(group_id, _default_cfg_toml))
            )
        )
