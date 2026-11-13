"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin

from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/", include("users.auth_urls")),
    path("api/users/", include("users.urls")),
    path("api/finance/", include("finance.urls")),
    path("api/accounting/", include("accounting.urls")),
    path("api/budgeting/", include("budgeting.urls")),
    path("api/institute/", include("institute.urls")),
    path("api/incubator/", include("incubator.urls")),
    path("api/marketing/", include("marketing.urls")),
    path("api/orientation/", include("orientation.urls")),
    path("api/preschool/", include("preschool.urls")),
]