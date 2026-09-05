from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django_mongodb_backend import transaction
from django.utils import timezone

from core.audit import log
from kyc.models import KycRequest


class KycRequestBusinessRuleError(Exception):
    pass


def determine_risk_band_from_score(risk_score_out_of_ten):
    if risk_score_out_of_ten <= 3:
        return "Low"
    if risk_score_out_of_ten <= 7:
        return "Medium"
    return "High"


def kyc_request_requires_supervisor_approval(kyc_request):
    return kyc_request.risk_score > 7


def get_kyc_request_by_human_readable_id(kyc_request_id):
    return KycRequest.objects.get(kyc_request_id=kyc_request_id)


def list_pending_kyc_requests_matching_filters(risk_band, name_search):
    pending_requests_matching_filters = KycRequest.objects.filter(
        status=KycRequest.Status.PENDING
    )
    normalized_name_search = name_search.strip()
    if normalized_name_search:
        pending_requests_matching_filters = pending_requests_matching_filters.filter(
            customer_name__icontains=normalized_name_search
        )

    normalized_risk_band = risk_band.title()
    risk_score_ranges_by_band = {
        "Low": (1, 3),
        "Medium": (4, 7),
        "High": (8, 10),
    }
    selected_risk_score_range = risk_score_ranges_by_band.get(normalized_risk_band)
    if selected_risk_score_range:
        minimum_risk_score, maximum_risk_score = selected_risk_score_range
        pending_requests_matching_filters = pending_requests_matching_filters.filter(
            risk_score__gte=minimum_risk_score,
            risk_score__lte=maximum_risk_score,
        )

    return list(
        pending_requests_matching_filters.order_by(
            "-risk_score", "submission_date", "kyc_request_id"
        )
    )


def list_reviewed_kyc_requests_matching_status_filter(status_filter):
    reviewed_requests_matching_status_filter = KycRequest.objects.exclude(
        status=KycRequest.Status.PENDING
    )
    normalized_status_filter = status_filter.title()
    if normalized_status_filter in {
        KycRequest.Status.APPROVED,
        KycRequest.Status.REJECTED,
    }:
        reviewed_requests_matching_status_filter = (
            reviewed_requests_matching_status_filter.filter(
                status=normalized_status_filter
            )
        )
    return list(
        reviewed_requests_matching_status_filter.order_by(
            "-reviewed_date", "-kyc_request_id"
        )
    )


def count_dashboard_kyc_request_totals():
    start_of_today = timezone.make_aware(
        datetime.combine(timezone.localdate(), time.min)
    )
    start_of_tomorrow = start_of_today + timedelta(days=1)
    reviewed_today = KycRequest.objects.filter(
        reviewed_date__gte=start_of_today,
        reviewed_date__lt=start_of_tomorrow,
    )
    return {
        "pending_count": KycRequest.objects.filter(
            status=KycRequest.Status.PENDING
        ).count(),
        "approved_today_count": reviewed_today.filter(
            status=KycRequest.Status.APPROVED
        ).count(),
        "rejected_today_count": reviewed_today.filter(
            status=KycRequest.Status.REJECTED
        ).count(),
    }


def validate_kyc_request_is_pending(kyc_request):
    if kyc_request.status != KycRequest.Status.PENDING:
        raise KycRequestBusinessRuleError(
            f"Request {kyc_request.kyc_request_id} has already been reviewed."
        )


def validate_supervisor_email_for_high_risk_approval(
    kyc_request,
    supervisor_email_from_form,
):
    request_requires_supervisor_approval = (
        kyc_request_requires_supervisor_approval(kyc_request)
    )
    if not request_requires_supervisor_approval:
        return ""

    normalized_supervisor_email = supervisor_email_from_form.strip()
    supervisor_email_is_valid = "@" in normalized_supervisor_email
    if not supervisor_email_is_valid:
        raise KycRequestBusinessRuleError(
            "A valid supervisor email is required for high-risk approvals."
        )
    return normalized_supervisor_email


def validate_reviewer_notes_for_rejection(reviewer_notes_from_form):
    normalized_reviewer_notes = reviewer_notes_from_form.strip()
    reviewer_notes_are_missing = not normalized_reviewer_notes
    if reviewer_notes_are_missing:
        raise KycRequestBusinessRuleError(
            "Reviewer notes are required before rejecting a request."
        )
    return normalized_reviewer_notes


@transaction.atomic
def approve_kyc_request_and_write_audit_log(
    kyc_request_id,
    reviewer_email,
    reviewer_notes,
    supervisor_email,
):
    kyc_request_to_approve = get_kyc_request_by_human_readable_id(kyc_request_id)
    validate_kyc_request_is_pending(kyc_request_to_approve)
    normalized_supervisor_email = (
        validate_supervisor_email_for_high_risk_approval(
            kyc_request_to_approve,
            supervisor_email,
        )
    )
    normalized_reviewer_notes = reviewer_notes.strip()
    old_status = kyc_request_to_approve.status
    reviewed_at = timezone.now()

    kyc_request_to_approve.status = KycRequest.Status.APPROVED
    kyc_request_to_approve.reviewed_by = reviewer_email
    kyc_request_to_approve.reviewed_date = reviewed_at
    kyc_request_to_approve.reviewer_notes = normalized_reviewer_notes
    kyc_request_to_approve.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_date",
            "reviewer_notes",
        ]
    )

    supervisor_detail = normalized_supervisor_email or "none"
    log(
        action="kyc_request_approved",
        user=reviewer_email,
        record_id=kyc_request_to_approve.kyc_request_id,
        details=(
            f"status: {old_status} -> {KycRequest.Status.APPROVED}; "
            f"supervisor: {supervisor_detail}; "
            f"notes: {normalized_reviewer_notes or 'none'}"
        ),
    )
    return kyc_request_to_approve


@transaction.atomic
def reject_kyc_request_and_write_audit_log(
    kyc_request_id,
    reviewer_email,
    reviewer_notes,
):
    kyc_request_to_reject = get_kyc_request_by_human_readable_id(kyc_request_id)
    validate_kyc_request_is_pending(kyc_request_to_reject)
    normalized_reviewer_notes = validate_reviewer_notes_for_rejection(
        reviewer_notes
    )
    old_status = kyc_request_to_reject.status
    reviewed_at = timezone.now()

    kyc_request_to_reject.status = KycRequest.Status.REJECTED
    kyc_request_to_reject.reviewed_by = reviewer_email
    kyc_request_to_reject.reviewed_date = reviewed_at
    kyc_request_to_reject.reviewer_notes = normalized_reviewer_notes
    kyc_request_to_reject.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_date",
            "reviewer_notes",
        ]
    )

    log(
        action="kyc_request_rejected",
        user=reviewer_email,
        record_id=kyc_request_to_reject.kyc_request_id,
        details=(
            f"status: {old_status} -> {KycRequest.Status.REJECTED}; "
            "supervisor: none; "
            f"notes: {normalized_reviewer_notes}"
        ),
    )
    return kyc_request_to_reject


@transaction.atomic
def create_seed_kyc_request_and_write_audit_log(
    kyc_request_id,
    customer_name,
    customer_email,
    risk_score,
    submission_date,
):
    existing_kyc_request = KycRequest.objects.filter(
        kyc_request_id=kyc_request_id
    ).first()
    if existing_kyc_request:
        return existing_kyc_request, False

    created_kyc_request = KycRequest.objects.create(
        kyc_request_id=kyc_request_id,
        customer_name=customer_name,
        customer_email=customer_email,
        risk_score=risk_score,
        submission_date=submission_date,
        status=KycRequest.Status.PENDING,
    )
    log(
        action="kyc_request_seeded",
        user="system@example.com",
        record_id=created_kyc_request.kyc_request_id,
        details="status: none -> Pending; supervisor: none; notes: none",
    )
    return created_kyc_request, True


def create_seed_users_and_pending_kyc_requests():
    user_model = get_user_model()
    seeded_user_definitions = [
        {
            "username": "reviewer",
            "email": "reviewer@example.com",
            "password": "reviewer",
        },
        {
            "username": "supervisor",
            "email": "supervisor@example.com",
            "password": "supervisor",
        },
    ]
    for seeded_user_definition in seeded_user_definitions:
        seeded_user, user_was_created = user_model.objects.get_or_create(
            username=seeded_user_definition["username"],
            defaults={"email": seeded_user_definition["email"]},
        )
        if user_was_created:
            seeded_user.set_password(seeded_user_definition["password"])
            seeded_user.save()

    today = timezone.localdate()
    seeded_kyc_request_definitions = [
        (1001, "Amina Yusuf", "amina.yusuf@example.com", 2, 1),
        (1002, "Ben Carter", "ben.carter@example.com", 3, 2),
        (1003, "Chloe Martin", "chloe.martin@example.com", 5, 3),
        (1004, "Diego Santos", "diego.santos@example.com", 7, 4),
        (1005, "Elena Petrova", "elena.petrova@example.com", 8, 5),
        (1006, "Farah Khan", "farah.khan@example.com", 10, 6),
        (1007, "Grace Lee", "grace.lee@example.com", 1, 7),
        (1008, "Hugo Bernard", "hugo.bernard@example.com", 4, 8),
    ]
    created_kyc_request_count = 0
    for (
        kyc_request_id,
        customer_name,
        customer_email,
        risk_score,
        days_ago_submitted,
    ) in seeded_kyc_request_definitions:
        _, kyc_request_was_created = create_seed_kyc_request_and_write_audit_log(
            kyc_request_id=kyc_request_id,
            customer_name=customer_name,
            customer_email=customer_email,
            risk_score=risk_score,
            submission_date=today - timedelta(days=days_ago_submitted),
        )
        if kyc_request_was_created:
            created_kyc_request_count += 1
    return created_kyc_request_count
