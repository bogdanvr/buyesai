from django.contrib.admin import AdminSite
from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group


class GroupedCRMAdminSite(AdminSite):
    site_header = "Buyes CRM Admin"
    site_title = "Buyes CRM Admin"
    index_title = "Управление CRM"

    admin_group_order = {
        "Пользователи и права": 5,
        "Лиды": 10,
        "Сделки": 20,
        "Компании и контакты": 30,
        "Коммуникации": 35,
        "Касания": 40,
        "Задачи и роли": 50,
        "Автоматизация": 60,
        "Интеграции": 70,
        "Сайт и формы": 80,
        "Контент": 90,
        "Прочее": 999,
    }

    def _resolve_admin_group(self, model_dict):
        object_name = str(model_dict.get("object_name") or "").strip()
        app_label = str(model_dict.get("app_label") or "").strip()
        for model, model_admin in self._registry.items():
            if model._meta.app_label == app_label and model.__name__ == object_name:
                return str(getattr(model_admin, "admin_group", "") or "").strip() or "Прочее"
        return "Прочее"

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label=app_label)
        for app in app_list:
            grouped_models = {}
            for model_dict in app.get("models", []):
                group_name = self._resolve_admin_group(model_dict)
                grouped_models.setdefault(group_name, []).append(model_dict)
            app["admin_groups"] = [
                {
                    "name": group_name,
                    "models": sorted(models, key=lambda entry: entry.get("name") or ""),
                }
                for group_name, models in sorted(
                    grouped_models.items(),
                    key=lambda item: (self.admin_group_order.get(item[0], 999), item[0]),
                )
            ]
        return app_list


crm_admin_site = GroupedCRMAdminSite(name="admin")


class CRMUserAdmin(UserAdmin):
    admin_group = "Пользователи и права"


class CRMGroupAdmin(GroupAdmin):
    admin_group = "Пользователи и права"


for model, model_admin in (
    (get_user_model(), CRMUserAdmin),
    (Group, CRMGroupAdmin),
):
    try:
        crm_admin_site.register(model, model_admin)
    except AlreadyRegistered:
        pass
