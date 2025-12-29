from django.urls import path

from .views import (
    DashboardSummaryView,
    DashboardRevenueView,
    DashboardOrdersByStatusView,
)

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view()),
    path("dashboard/revenue/", DashboardRevenueView.as_view()),
    path("dashboard/orders-by-status/", DashboardOrdersByStatusView.as_view()),
]
