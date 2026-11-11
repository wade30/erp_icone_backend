from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from users.permissions import ERPModulePermission, ServiceScopedQuerysetMixin


class BaseQueryView:
    def get_queryset(self):
        return self.queryset


class ScopedTestView(ServiceScopedQuerysetMixin, BaseQueryView):
    pass


class ERPModulePermissionTests(SimpleTestCase):
    def setUp(self):
        self.permission = ERPModulePermission()

    def make_user(self, role=None, service="GENERAL", active=True, authenticated=True):
        return SimpleNamespace(
            is_authenticated=authenticated,
            is_active=active,
            role=role,
            service=service,
        )

    def make_request(self, user, method="GET", data=None):
        return SimpleNamespace(user=user, method=method, data=data or {})

    def make_view(self, action, module, service_field=None):
        return SimpleNamespace(
            action=action,
            permission_module=module,
            permission_service_field=service_field,
        )

    def check_permission(
        self,
        role,
        action,
        module,
        service="GENERAL",
        active=True,
        authenticated=True,
        method="GET",
        data=None,
        service_field=None,
    ):
        user = self.make_user(
            role=role,
            service=service,
            active=active,
            authenticated=authenticated,
        )
        request = self.make_request(user, method=method, data=data)
        view = self.make_view(action, module, service_field)
        return self.permission.has_permission(request, view)

    def test_anonymous_and_inactive_users_are_denied(self):
        self.assertFalse(self.check_permission(
            "DIRECTOR", "list", "finance", authenticated=False
        ))
        self.assertFalse(self.check_permission(
            "DIRECTOR", "list", "finance", active=False
        ))

    def test_leadership_roles_in_general_department_can_read_all_modules(self):
        for role in ("SECRETARY", "FINANCE", "DIRECTOR", "PDG"):
            with self.subTest(role=role):
                self.assertTrue(self.check_permission(
                    role, "list", "orientation"
                ))

    def test_service_manager_cannot_read_other_services(self):
        self.assertFalse(self.check_permission(
            "SERVICE_MANAGER", "list", "finance", service="INSTITUTE"
        ))

    def test_service_manager_can_only_write_their_service_module(self):
        self.assertTrue(self.check_permission(
            "SERVICE_MANAGER", "update", "institute", service="INSTITUTE"
        ))
        self.assertFalse(self.check_permission(
            "SERVICE_MANAGER", "update", "marketing", service="INSTITUTE"
        ))

    def test_service_manager_cannot_change_record_service(self):
        self.assertFalse(self.check_permission(
            "SERVICE_MANAGER",
            "partial_update",
            "finance",
            service="INSTITUTE",
            method="PATCH",
            data={"service": "MARKETING"},
            service_field="service",
        ))

    def test_general_finance_role_can_create_finance_records_for_operational_services(self):
        for service in ("INSTITUTE", "INCUBATOR", "MARKETING", "ORIENTATION"):
            with self.subTest(service=service):
                self.assertTrue(self.check_permission(
                    "FINANCE",
                    "create",
                    "finance",
                    service="INSTITUTE",
                    method="POST",
                    data={"service": service},
                    service_field="service",
                ))

    def test_general_finance_role_cannot_assign_general_or_unknown_service(self):
        for service in ("GENERAL", "UNKNOWN"):
            with self.subTest(service=service):
                self.assertFalse(self.check_permission(
                    "FINANCE",
                    "create",
                    "finance",
                    service="INSTITUTE",
                    method="POST",
                    data={"service": service},
                    service_field="service",
                ))

    def test_general_finance_role_can_access_finance_records_from_any_service(self):
        request = self.make_request(
            self.make_user("FINANCE", service="INSTITUTE"),
            method="PATCH",
        )
        view = self.make_view("partial_update", "finance", "service")
        for service in ("INSTITUTE", "INCUBATOR", "MARKETING", "ORIENTATION"):
            with self.subTest(service=service):
                self.assertTrue(self.permission.has_object_permission(
                    request,
                    view,
                    SimpleNamespace(service=service),
                ))

    def test_finance_role_can_read_finance_records_from_any_service(self):
        self.assertTrue(self.check_permission(
            "FINANCE",
            "list",
            "finance",
            service="INSTITUTE",
            service_field="service",
        ))

    def test_finance_role_gets_unfiltered_finance_queryset(self):
        queryset = Mock()
        view = ScopedTestView()
        view.queryset = queryset
        view.permission_service_field = "service"
        view.permission_module = "finance"
        view.request = SimpleNamespace(
            user=self.make_user("FINANCE", service="INSTITUTE"),
            method="GET",
        )

        self.assertIs(view.get_queryset(), queryset)
        queryset.filter.assert_not_called()

    def test_service_manager_can_submit_expense_requests_for_their_service(self):
        self.assertTrue(self.check_permission(
            "SERVICE_MANAGER",
            "submit",
            "finance",
            service="INSTITUTE",
            method="POST",
            data={},
            service_field="service",
        ))

    def test_staff_access_is_limited_to_their_service_module(self):
        self.assertTrue(self.check_permission(
            "STAFF", "list", "institute", service="INSTITUTE"
        ))
        self.assertFalse(self.check_permission(
            "STAFF", "list", "marketing", service="INSTITUTE"
        ))
        self.assertFalse(self.check_permission(
            "STAFF", "list", "finance", service="INSTITUTE"
        ))

    def test_staff_cannot_create_data_for_another_service(self):
        self.assertFalse(self.check_permission(
            "STAFF",
            "create",
            "marketing",
            service="MARKETING",
            method="POST",
            data={"service": "ORIENTATION"},
            service_field="service",
        ))

    def test_accountant_cannot_approve_expenses(self):
        self.assertFalse(self.check_permission(
            "ACCOUNTANT", "approve", "finance"
        ))

    def test_service_user_cannot_read_shared_accounting_catalogs(self):
        user = self.make_user("SERVICE_MANAGER", service="MARKETING")
        request = self.make_request(user)
        view = self.make_view("list", "accounting")
        view.permission_shared_data = True
        self.assertFalse(self.permission.has_permission(request, view))

    def test_unknown_roles_modules_and_actions_are_denied(self):
        self.assertFalse(self.check_permission(
            "UNKNOWN", "list", "finance", service="INCUBATOR"
        ))
        self.assertFalse(self.check_permission(
            "DIRECTOR", "list", None
        ))
        self.assertFalse(self.check_permission(
            "DIRECTOR", "unknown_action", "finance"
        ))

    def test_service_object_access_is_checked(self):
        request = self.make_request(
            self.make_user("STAFF", service="INSTITUTE")
        )
        view = self.make_view("retrieve", "marketing", "service")
        self.assertFalse(self.permission.has_object_permission(
            request, view, SimpleNamespace(service="MARKETING")
        ))
        self.assertTrue(self.permission.has_object_permission(
            request, view, SimpleNamespace(service="INSTITUTE")
        ))

    def test_related_service_object_access_is_checked(self):
        request = self.make_request(
            self.make_user("STAFF", service="INSTITUTE")
        )
        view = self.make_view("retrieve", "accounting", "lines__service")
        lines = Mock()
        lines.filter.return_value.exists.return_value = True
        self.assertTrue(self.permission.has_object_permission(
            request, view, SimpleNamespace(lines=lines)
        ))
        lines.filter.assert_called_once_with(service="INSTITUTE")

    def test_queryset_is_filtered_to_the_users_service(self):
        queryset = Mock()
        filtered_queryset = Mock()
        queryset.filter.return_value = filtered_queryset
        view = ScopedTestView()
        view.queryset = queryset
        view.permission_service_field = "service"
        view.request = SimpleNamespace(
            user=self.make_user("STAFF", service="INSTITUTE"),
            method="GET",
        )

        view.get_queryset()

        queryset.filter.assert_called_once_with(service="INSTITUTE")
        filtered_queryset.distinct.assert_called_once_with()

    def test_service_manager_queryset_is_scoped_for_reading(self):
        queryset = Mock()
        filtered_queryset = Mock()
        queryset.filter.return_value = filtered_queryset
        view = ScopedTestView()
        view.queryset = queryset
        view.permission_service_field = "service"
        view.request = SimpleNamespace(
            user=self.make_user("SERVICE_MANAGER", service="INSTITUTE"),
            method="GET",
        )

        view.get_queryset()

        queryset.filter.assert_called_once_with(service="INSTITUTE")
        filtered_queryset.distinct.assert_called_once_with()

    def test_queryset_for_an_unrelated_module_is_empty(self):
        queryset = Mock()
        empty_queryset = Mock()
        queryset.none.return_value = empty_queryset
        view = ScopedTestView()
        view.queryset = queryset
        view.permission_module = "marketing"
        view.request = SimpleNamespace(
            user=self.make_user("SERVICE_MANAGER", service="INCUBATOR"),
            method="GET",
        )

        self.assertIs(view.get_queryset(), empty_queryset)
        queryset.none.assert_called_once_with()

    def test_director_can_read_all_services_but_writes_remain_service_scoped(self):
        self.assertTrue(self.check_permission(
            "DIRECTOR", "list", "marketing", service="INCUBATOR"
        ))
        self.assertFalse(self.check_permission(
            "DIRECTOR", "update", "marketing", service="INCUBATOR",
            method="PATCH",
        ))
        self.assertTrue(self.check_permission(
            "DIRECTOR", "update", "incubator", service="INCUBATOR",
            method="PATCH",
        ))

    def test_general_department_has_global_read_access(self):
        self.assertTrue(self.check_permission(
            "STAFF", "list", "marketing", service="GENERAL"
        ))
        self.assertFalse(self.check_permission(
            "DIRECTOR", "update", "marketing", service="GENERAL",
            method="PATCH",
        ))
        self.assertTrue(self.check_permission(
            "DIRECTOR", "update", "finance", service="GENERAL",
            method="PATCH",
        ))
