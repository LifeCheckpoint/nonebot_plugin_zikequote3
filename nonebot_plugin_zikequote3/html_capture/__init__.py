"""
HTML 截图子包。

底层实现位于 ``screen_shot`` 模块。上层应通过 DI 容器获取
``HtmlRenderServiceBase`` 并调用 ``render()`` 方法来完成截图。
"""
