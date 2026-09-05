from django.urls import path

from kyc import views


app_name = "kyc"

urlpatterns = [
    path(
        "",
        views.show_kyc_review_dashboard,
        name="show_kyc_review_dashboard",
    ),
    path(
        "requests/<int:kyc_request_id>/",
        views.show_kyc_request_review_detail,
        name="show_kyc_request_review_detail",
    ),
    path(
        "requests/<int:kyc_request_id>/decision/",
        views.submit_kyc_request_decision,
        name="submit_kyc_request_decision",
    ),
    path(
        "history/",
        views.show_reviewed_kyc_request_history,
        name="show_reviewed_kyc_request_history",
    ),
]
