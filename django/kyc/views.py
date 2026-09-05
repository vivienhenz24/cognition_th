from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render

from kyc.forms import KycRequestDecisionForm
from kyc.models import KycRequest
from kyc.services import (
    KycRequestBusinessRuleError,
    approve_kyc_request_and_write_audit_log,
    count_dashboard_kyc_request_totals,
    determine_risk_band_from_score,
    get_kyc_request_by_human_readable_id,
    kyc_request_requires_supervisor_approval,
    list_pending_kyc_requests_matching_filters,
    list_reviewed_kyc_requests_matching_status_filter,
    reject_kyc_request_and_write_audit_log,
    validate_reviewer_notes_for_rejection,
)


def build_pending_request_rows_for_template(pending_requests):
    return [
        {
            "kyc_request": pending_request,
            "risk_band": determine_risk_band_from_score(
                pending_request.risk_score
            ),
        }
        for pending_request in pending_requests
    ]


def request_is_partial_htmx_update(request):
    return request.htmx and not request.htmx.history_restore_request


def show_kyc_review_dashboard(request):
    selected_risk_band = request.GET.get("risk_band", "All")
    customer_name_search = request.GET.get("name_search", "")
    pending_requests = list_pending_kyc_requests_matching_filters(
        selected_risk_band,
        customer_name_search,
    )
    context = {
        "dashboard_totals": count_dashboard_kyc_request_totals(),
        "pending_request_rows": build_pending_request_rows_for_template(
            pending_requests
        ),
        "selected_risk_band": selected_risk_band,
        "customer_name_search": customer_name_search,
        "risk_band_options": ["All", "Low", "Medium", "High"],
    }
    if request_is_partial_htmx_update(request):
        return render(request, "kyc/partials/pending_request_results.html", context)
    return render(request, "kyc/dashboard.html", context)


def show_kyc_request_review_detail(request, kyc_request_id):
    try:
        selected_kyc_request = get_kyc_request_by_human_readable_id(
            kyc_request_id
        )
    except KycRequest.DoesNotExist as missing_request_error:
        raise Http404("The requested KYC request does not exist.") from missing_request_error

    decision_form = KycRequestDecisionForm(
        initial={"reviewer_notes": selected_kyc_request.reviewer_notes}
    )
    context = build_kyc_request_detail_context(
        selected_kyc_request,
        decision_form,
    )
    return render(request, "kyc/review_detail.html", context)


def submit_kyc_request_decision(request, kyc_request_id):
    if request.method != "POST":
        return redirect(
            "kyc:show_kyc_request_review_detail",
            kyc_request_id=kyc_request_id,
        )
    try:
        selected_kyc_request = get_kyc_request_by_human_readable_id(
            kyc_request_id
        )
    except KycRequest.DoesNotExist as missing_request_error:
        raise Http404("The requested KYC request does not exist.") from missing_request_error

    decision_form = KycRequestDecisionForm(request.POST)
    if not decision_form.is_valid():
        context = build_kyc_request_detail_context(
            selected_kyc_request,
            decision_form,
        )
        return render(request, "kyc/review_detail.html", context, status=400)

    selected_decision = request.POST.get("decision", "")
    decision_is_confirmed = request.POST.get("confirmation") == "confirmed"
    reviewer_notes_from_form = decision_form.cleaned_data["reviewer_notes"]
    supervisor_email_from_form = decision_form.cleaned_data["supervisor_email"]

    if selected_decision == "reject" and not decision_is_confirmed:
        try:
            validate_reviewer_notes_for_rejection(reviewer_notes_from_form)
        except KycRequestBusinessRuleError as business_rule_error:
            decision_form.add_error("reviewer_notes", str(business_rule_error))
            context = build_kyc_request_detail_context(
                selected_kyc_request,
                decision_form,
            )
            return render(request, "kyc/review_detail.html", context, status=400)
        context = build_kyc_request_detail_context(
            selected_kyc_request,
            decision_form,
            confirmation_action="reject",
        )
        return render(request, "kyc/review_detail.html", context)

    approval_requires_confirmation = (
        selected_decision == "approve"
        and kyc_request_requires_supervisor_approval(selected_kyc_request)
    )
    if approval_requires_confirmation and not decision_is_confirmed:
        context = build_kyc_request_detail_context(
            selected_kyc_request,
            decision_form,
            confirmation_action="approve",
        )
        return render(request, "kyc/review_detail.html", context)

    reviewer_email = request.user.email
    if not reviewer_email:
        decision_form.add_error(
            None,
            "Your account needs an email address before you can review requests.",
        )
        context = build_kyc_request_detail_context(
            selected_kyc_request,
            decision_form,
        )
        return render(request, "kyc/review_detail.html", context, status=400)

    try:
        if selected_decision == "approve":
            approve_kyc_request_and_write_audit_log(
                kyc_request_id=selected_kyc_request.kyc_request_id,
                reviewer_email=reviewer_email,
                reviewer_notes=reviewer_notes_from_form,
                supervisor_email=supervisor_email_from_form,
            )
            messages.success(
                request,
                f"KYC request {selected_kyc_request.kyc_request_id} was approved.",
            )
        elif selected_decision == "reject":
            reject_kyc_request_and_write_audit_log(
                kyc_request_id=selected_kyc_request.kyc_request_id,
                reviewer_email=reviewer_email,
                reviewer_notes=reviewer_notes_from_form,
            )
            messages.success(
                request,
                f"KYC request {selected_kyc_request.kyc_request_id} was rejected.",
            )
        else:
            decision_form.add_error(None, "Choose Approve or Reject to continue.")
            context = build_kyc_request_detail_context(
                selected_kyc_request,
                decision_form,
            )
            return render(request, "kyc/review_detail.html", context, status=400)
    except KycRequestBusinessRuleError as business_rule_error:
        decision_form.add_error(None, str(business_rule_error))
        context = build_kyc_request_detail_context(
            selected_kyc_request,
            decision_form,
            confirmation_action=(
                selected_decision if decision_is_confirmed else ""
            ),
        )
        return render(request, "kyc/review_detail.html", context, status=400)

    return redirect("kyc:show_kyc_review_dashboard")


def build_kyc_request_detail_context(
    selected_kyc_request,
    decision_form,
    confirmation_action="",
):
    return {
        "selected_kyc_request": selected_kyc_request,
        "risk_band": determine_risk_band_from_score(
            selected_kyc_request.risk_score
        ),
        "request_requires_supervisor_approval": (
            kyc_request_requires_supervisor_approval(selected_kyc_request)
        ),
        "decision_form": decision_form,
        "confirmation_action": confirmation_action,
    }


def show_reviewed_kyc_request_history(request):
    selected_status_filter = request.GET.get("status", "All")
    reviewed_requests = list_reviewed_kyc_requests_matching_status_filter(
        selected_status_filter
    )
    context = {
        "reviewed_requests": reviewed_requests,
        "selected_status_filter": selected_status_filter,
        "status_filter_options": ["All", "Approved", "Rejected"],
    }
    if request_is_partial_htmx_update(request):
        return render(
            request,
            "kyc/partials/reviewed_request_results.html",
            context,
        )
    return render(request, "kyc/history.html", context)
