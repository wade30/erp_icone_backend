
from rest_framework.permissions import BasePermission


# ============================================================
# 1. RÔLES ET SERVICES
# ============================================================

LEADERSHIP_ROLES = {
    "SECRETARY",
    "DIRECTOR",
    "PDG",
}

FULL_ACCESS_ROLES = {
    "DIRECTOR",
    "PDG",
}

GLOBAL_READ_ROLES = {
    "SECRETARY",
    "DIRECTOR",
    "PDG",
}

SERVICE_ROLES = {
    "SERVICE_MANAGER",
    "STAFF",
}

FINANCE_ROLES = {
    "FINANCE",
    "ACCOUNTANT",
}

MODULE_SERVICES = {
    "institute": "INSTITUTE",
    "incubator": "INCUBATOR",
    "marketing": "MARKETING",
    "orientation": "ORIENTATION",
    "preschool": "PRESCHOOL",
    "finance": "GENERAL",
    "accounting": "GENERAL",
    "budgeting": "GENERAL",
}

FINANCE_SERVICES = {
    "INSTITUTE",
    "INCUBATOR",
    "MARKETING",
    "ORIENTATION",
    "PRESCHOOL",
}


# ============================================================
# 2. PERMISSIONS PAR RÔLE
# ============================================================

ROLE_PERMISSIONS = {

    "DIRECTOR": {
        "*": {
            "read",
            "create",
            "update",
            "delete",
            "approve",
            "pay",
            "post",
            "submit",
        }
    },

    "PDG": {
        "*": {
            "read",
            "create",
            "update",
            "delete",
            "approve",
            "pay",
            "post",
            "submit",
        }
    },

    "SECRETARY": {
        "*": {"read"},
    },

    # Service financier
    "FINANCE": {
        "finance": {
            "read",
            "create",
            "update",
            "approve",
            "pay",
        },
        "budgeting": {
            "read",
            "create",
            "update",
            "approve",
        },
        "accounting": {
            "read",
        },
    },

    # Comptable
    "ACCOUNTANT": {
        "finance": {
            "read",
        },
        "budgeting": {
            "read",
        },
        "accounting": {
            "read",
            "create",
            "update",
            "post",
        },
    },

    # Responsables opérationnels
    "SERVICE_MANAGER": {
        "institute": {"read", "create", "update"},
        "incubator": {"read", "create", "update"},
        "marketing": {"read", "create", "update"},
        "orientation": {"read", "create", "update"},
        "preschool": {"read", "create", "update"},
        "finance": {"read"},
        "budgeting": {"read", "create", "update"},
    },

    # Agents opérationnels
    "STAFF": {
        "institute": {"read", "create"},
        "incubator": {"read", "create"},
        "marketing": {"read", "create"},
        "orientation": {"read", "create"},
        "preschool": {"read", "create"},
    },
}

KNOWN_ROLES = set(ROLE_PERMISSIONS)


# ============================================================
# 3. CORRESPONDANCE DES ACTIONS
# ============================================================

ACTION_MAP = {
    "list": "read",
    "retrieve": "read",

    "create": "create",

    "update": "update",
    "partial_update": "update",

    "destroy": "delete",

    "complete": "update",
    "submit": "submit",
    "approve": "approve",
    "reject": "approve",
    "validate": "approve",

    "pay": "pay",
    "post": "post",
}


# ============================================================
# 4. NORMALISATION DES UTILISATEURS
# ============================================================

def normalize_value(value):
    if hasattr(value, "code"):
        value = value.code

    if hasattr(value, "value"):
        value = value.value

    return str(value or "").upper()


def get_user_role(user):
    return normalize_value(
        getattr(user, "role", None)
    )


def get_user_service(user):
    return normalize_value(
        getattr(user, "service", None)
    )


def get_module(view):
    return getattr(view, "permission_module", None)


def get_action(view):
    return ACTION_MAP.get(
        getattr(view, "action", None)
    )


# ============================================================
# 5. ACCÈS TRANSVERSAUX
# ============================================================

def has_global_read_access(user):
    return get_user_role(user) in GLOBAL_READ_ROLES


def has_global_finance_access(user, module):
    return (
        module == "finance"
        and get_user_role(user) in FINANCE_ROLES
    )


def has_global_accounting_access(user, module):
    return (
        module == "accounting"
        and get_user_role(user) in FINANCE_ROLES
    )


def has_global_budget_access(user, module):
    return (
        module == "budgeting"
        and get_user_role(user) in FINANCE_ROLES
    )


def has_global_module_access(user, module):

    if has_global_read_access(user):
        return True

    if has_global_finance_access(user, module):
        return True

    if has_global_accounting_access(user, module):
        return True

    if has_global_budget_access(user, module):
        return True

    return False


def user_owns_module(user, module):

    expected_service = MODULE_SERVICES.get(module)

    return (
        expected_service is not None
        and get_user_service(user) == expected_service
        and get_user_role(user) in {
            "DIRECTOR",
            "PDG",
            "SERVICE_MANAGER",
            "STAFF",
        }
    )


# ============================================================
# 6. PERMISSIONS PERSONNALISÉES
# ============================================================

def get_role_actions(user, view, module):

    role = get_user_role(user)

    custom_permissions = getattr(
        view,
        "permission_role_actions",
        {},
    )

    if role in custom_permissions:
        return set(custom_permissions[role])

    permissions = ROLE_PERMISSIONS.get(role, {})

    return (
        set(permissions.get(module, set()))
        | set(permissions.get("*", set()))
    )


# ============================================================
# 7. DEMANDES DE DÉPENSES
# ============================================================

def is_operational_request_view(view):
    return getattr(
        view,
        "permission_operational_request",
        False,
    )


def can_manage_operational_request(user, view, action):

    if not is_operational_request_view(view):
        return None

    if action not in {
        "create",
        "update",
        "submit",
    }:
        return None

    if get_user_role(user) not in SERVICE_ROLES:
        return False

    return get_user_service(user) in FINANCE_SERVICES


# ============================================================
# 8. AUTORISATION DES ACTIONS
# ============================================================

def can_access_module(user, module, action, view):

    operational_permission = can_manage_operational_request(
        user,
        view,
        action,
    )

    if operational_permission is not None:
        return operational_permission

    allowed_actions = get_role_actions(
        user,
        view,
        module,
    )

    return action in allowed_actions


# ============================================================
# 9. CONTRÔLE DE L'APPARTENANCE AU SERVICE
# ============================================================

def object_service_value(instance, service_field):

    value = instance

    for attribute in service_field.split("__"):

        if value is None:
            return None

        value = getattr(
            value,
            attribute,
            None,
        )

    return value


def _object_belongs_to_service(
    instance,
    service_field,
    service,
):

    value = object_service_value(
        instance,
        service_field,
    )

    if value is None:
        return False

    return normalize_value(value) == service


def can_access_object_service(
    user,
    module,
    obj,
    view,
):

    if has_global_module_access(user, module):
        return True

    if getattr(view, "permission_shared_data", False):
        return (
            get_user_role(user) == "ACCOUNTANT"
        )

    service_field = getattr(
        view,
        "permission_service_field",
        None,
    )

    if service_field:
        return _object_belongs_to_service(
            obj,
            service_field,
            get_user_service(user),
        )

    return user_owns_module(
        user,
        module,
    )


# ============================================================
# 10. FILTRAGE AUTOMATIQUE DES QUERYSETS
# ============================================================

class ServiceScopedQuerysetMixin:

    def get_queryset(self):

        queryset = super().get_queryset()
        user = self.request.user

        if (
            not user
            or not user.is_authenticated
            or not user.is_active
        ):
            return queryset.none()

        module = get_module(self)
        action = get_action(self)

        if not module or not action:
            return queryset.none()

        if not can_access_module(
            user,
            module,
            action,
            self,
        ):
            return queryset.none()

        # Accès transversal.
        if has_global_module_access(user, module):
            return queryset

        # Données partagées.
        if getattr(self, "permission_shared_data", False):
            if get_user_role(user) == "ACCOUNTANT":
                return queryset

            return queryset.none()

        service_field = getattr(
            self,
            "permission_service_field",
            None,
        )

        if service_field:

            service = get_user_service(user)

            if not service or service == "GENERAL":
                return queryset.none()

            return queryset.filter(
                **{
                    service_field: service,
                }
            ).distinct()

        if user_owns_module(user, module):
            return queryset

        return queryset.none()


# ============================================================
# 11. PERMISSION PRINCIPALE DE L'ERP
# ============================================================

class ERPModulePermission(BasePermission):

    def has_permission(self, request, view):

        user = request.user

        if (
            not user
            or not user.is_authenticated
            or not user.is_active
        ):
            return False

        role = get_user_role(user)

        if role not in KNOWN_ROLES:
            return False

        module = get_module(view)
        action = get_action(view)

        if not module or not action:
            return False

        if not can_access_module(
            user,
            module,
            action,
            view,
        ):
            return False

        # Lecture.
        if action == "read":

            if has_global_module_access(user, module):
                return True

            if getattr(view, "permission_shared_data", False):
                return role == "ACCOUNTANT"

            service_field = getattr(
                view,
                "permission_service_field",
                None,
            )

            if service_field:
                service = get_user_service(user)

                return bool(
                    service
                    and service != "GENERAL"
                )

            return user_owns_module(user, module)

        # Données partagées :
        # les écritures sont limitées aux rôles explicitement autorisés.
        if getattr(view, "permission_shared_data", False):

            allowed_roles = getattr(
                view,
                "permission_shared_write_roles",
                {"ACCOUNTANT"},
            )

            return role in allowed_roles

        # Contrôle du service pour les écritures.
        service_field = getattr(
            view,
            "permission_service_field",
            None,
        )

        if service_field:

            # Pour les champs directement stockés sur le modèle.
            # Exemple : Receipt.service ou Budget.service.
            # Pour les relations comme budget__service,
            # le serializer contrôle le parent.
            input_field = getattr(
                view,
                "permission_service_input_field",
                None,
            )

            if input_field is None and "__" not in service_field:
                input_field = service_field

            if input_field:

                service_value = request.data.get(input_field)

                if action == "create" and not service_value:

                    # Les demandes peuvent reprendre automatiquement
                    # le service du demandeur.
                    if not (
                        is_operational_request_view(view)
                        and role in SERVICE_ROLES
                    ):
                        return False

                if service_value:

                    service_value = normalize_value(service_value)
                    user_service = get_user_service(user)

                    if is_operational_request_view(view):

                        if service_value != user_service:
                            return False

                    elif role in FULL_ACCESS_ROLES:

                        if service_value not in (
                            FINANCE_SERVICES | {"GENERAL"}
                        ):
                            return False

                    elif has_global_finance_access(user, module):

                        if service_value not in FINANCE_SERVICES:
                            return False

                    elif service_value != user_service:
                        return False

            # Pour les relations, le serializer vérifie
            # l'appartenance du parent au service autorisé.

        elif not (
            user_owns_module(user, module)
            or has_global_module_access(user, module)
        ):
            return False

        return True

    # ========================================================
    # 12. PERMISSIONS SUR UN OBJET
    # ========================================================

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):

        user = request.user

        if (
            not user
            or not user.is_authenticated
            or not user.is_active
        ):
            return False

        module = get_module(view)
        action = get_action(view)

        if not module or not action:
            return False

        if not can_access_module(
            user,
            module,
            action,
            view,
        ):
            return False

        if has_global_module_access(user, module):
            return True

        if getattr(view, "permission_shared_data", False):
            return (
                action == "read"
                and get_user_role(user) == "ACCOUNTANT"
            )

        if is_operational_request_view(view):

            if get_user_role(user) not in SERVICE_ROLES:
                return False

        return can_access_object_service(
            user,
            module,
            obj,
            view,
        )
