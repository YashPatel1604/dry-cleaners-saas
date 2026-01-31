from django.urls import path

from .views import (
    DailyCashCloseReportCsvView,
    DailyCashCloseReportRangeView,
    DailyCashCloseReportView,
    CashDrawerReportView,
    OpsSummaryReportView,
    RevenueReportView,
    SettlementBreakdownReportView,
    TopCustomersReportView,
    WorkloadReportView,
)

urlpatterns = [
    path("daily-cash-close/", DailyCashCloseReportView.as_view()),
    path("daily-cash-close/range/", DailyCashCloseReportRangeView.as_view()),
    path("daily-cash-close.csv", DailyCashCloseReportCsvView.as_view()),
    path("cash-drawer/", CashDrawerReportView.as_view(), name="cash-drawer"),
    path("ops-summary/", OpsSummaryReportView.as_view(), name="ops-summary"),
    path("revenue/", RevenueReportView.as_view(), name="revenue-report"),
    path("settlement-breakdown/", SettlementBreakdownReportView.as_view(), name="settlement-breakdown"),
    path("customers/top/", TopCustomersReportView.as_view(), name="top-customers"),
    path("workload/", WorkloadReportView.as_view(), name="workload-report"),
]
