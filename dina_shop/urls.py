"""
URL configuration for dina_shop project.

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

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import IsAuthenticated

admin.site.site_header = "ImportHub Administration"
admin.site.site_title = "ImportHub Admin"
admin.site.index_title = "Business operations"

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/custom/", include("custom.urls")),
    path("api/catalog/", include("catalog.urls")),
    path("api/inventory/", include("inventory.urls")),
    path("api/people/", include("people.urls")),
    path("api/order/", include("order.urls")),
    path("api/payment/", include("payment.urls")),
    path("api/fulfillment/", include("fulfillment.urls")),
    path("api/public/", include("storefront.urls")),
    path("api/", include("dina_shop.reporting.urls")),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[IsAuthenticated]),
        name="api-schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="api-schema",
            permission_classes=[IsAuthenticated],
        ),
        name="api-docs",
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
