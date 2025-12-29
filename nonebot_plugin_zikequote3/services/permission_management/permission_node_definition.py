from nonebot_plugin_access_control_api.service.interface import IPluginService, ISubService

class PermissionServiceNodes:
    def __init__(self, n_perm_s: IPluginService):
        """
        定义插件的服务节点，用于精细化的权限控制

        Args:
            n_perm_s (IPluginService): 通过 `create_plugin_service` 创建的插件服务实例
        """
        self.n_perm_s = n_perm_s
        self.n_becollected: ISubService = n_perm_s.create_subservice("be_collected")
        self.n_becollected_llm: ISubService = self.n_becollected.create_subservice("llm")
        self.n_becollected_manual: ISubService = self.n_becollected.create_subservice("manual")
        self.n_get: ISubService = n_perm_s.create_subservice("get")
        self.n_get_text: ISubService = self.n_get.create_subservice("text")
        self.n_get_card: ISubService = self.n_get.create_subservice("card")
        self.n_get_image: ISubService = self.n_get.create_subservice("image")
        self.n_search: ISubService = n_perm_s.create_subservice("search")
        self.n_ranking: ISubService = n_perm_s.create_subservice("ranking")
        self.n_listing: ISubService = n_perm_s.create_subservice("listing")
        self.n_listing_self: ISubService = self.n_listing.create_subservice("self")
        self.n_listing_others: ISubService = self.n_listing.create_subservice("others")
        self.n_review: ISubService = n_perm_s.create_subservice("review")
        self.n_review_add: ISubService = self.n_review.create_subservice("add")
        self.n_review_delete: ISubService = self.n_review.create_subservice("delete")
        self.n_review_delete_self: ISubService = self.n_review_delete.create_subservice("self")
        self.n_review_delete_others: ISubService = self.n_review_delete.create_subservice("others")
        self.n_quote: ISubService = n_perm_s.create_subservice("quote")
        self.n_quote_add: ISubService = self.n_quote.create_subservice("add")
        self.n_quote_add_text: ISubService = self.n_quote_add.create_subservice("text")
        self.n_quote_add_image: ISubService = self.n_quote_add.create_subservice("image")
        self.n_quote_delete: ISubService = self.n_quote.create_subservice("delete")
        self.n_quote_delete_self: ISubService = self.n_quote_delete.create_subservice("self")
        self.n_quote_delete_others: ISubService = self.n_quote_delete.create_subservice("others")
        self.n_quote_attachimage: ISubService = self.n_quote.create_subservice("attach_image")
        self.n_quote_removeimage: ISubService = self.n_quote.create_subservice("remove_image")
        self.n_settings: ISubService = n_perm_s.create_subservice("settings")
        self.n_settings_get: ISubService = self.n_settings.create_subservice("get")
        self.n_settings_modify: ISubService = self.n_settings.create_subservice("modify")
        self.n_settings_modify_group: ISubService = self.n_settings_modify.create_subservice("group")
        self.n_settings_modify_global: ISubService = self.n_settings_modify.create_subservice("global")
        self.n_settings_reset: ISubService = self.n_settings.create_subservice("reset")
        self.n_settings_reset_group: ISubService = self.n_settings_reset.create_subservice("group")
        self.n_settings_reset_global: ISubService = self.n_settings_reset.create_subservice("global")
        self.n_forcerefresh: ISubService = n_perm_s.create_subservice("force_refresh")
        self.n_group_migration: ISubService = n_perm_s.create_subservice("group_migration")
        self.n_others: ISubService = n_perm_s.create_subservice("others")
