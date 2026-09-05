from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import AuditLog
from kyc.models import KycRequest
from kyc.services import (
    KycRequestBusinessRuleError,
    approve_kyc_request_and_write_audit_log,
    count_dashboard_kyc_request_totals,
    create_seed_users_and_pending_kyc_requests,
    determine_risk_band_from_score,
    list_pending_kyc_requests_matching_filters,
    list_reviewed_kyc_requests_matching_status_filter,
    reject_kyc_request_and_write_audit_log,
)


class KycRequestServicesTests(TestCase):
    def setUp(self):
        self.pending_low_risk_request = KycRequest.objects.create(
            kyc_request_id=2001,
            customer_name="Alice Example",
            customer_email="alice@example.com",
            risk_score=3,
            submission_date=timezone.localdate() - timedelta(days=2),
        )
        self.pending_high_risk_request = KycRequest.objects.create(
            kyc_request_id=2002,
            customer_name="Bob Example",
            customer_email="bob@example.com",
            risk_score=9,
            submission_date=timezone.localdate() - timedelta(days=1),
        )

    def test_risk_band_boundaries_match_the_specification(self):
        expected_bands_by_risk_score = {
            1: "Low",
            3: "Low",
            4: "Medium",
            7: "Medium",
            8: "High",
            10: "High",
        }
        for risk_score, expected_band in expected_bands_by_risk_score.items():
            with self.subTest(risk_score=risk_score):
                self.assertEqual(
                    determine_risk_band_from_score(risk_score),
                    expected_band,
                )

    def test_low_risk_approval_without_supervisor_updates_request_and_writes_one_audit_row(
        self,
    ):
        approve_kyc_request_and_write_audit_log(
            kyc_request_id=2001,
            reviewer_email="reviewer@example.com",
            reviewer_notes="Identity documents verified.",
            supervisor_email="not-applicable@example.com",
        )

        self.pending_low_risk_request.refresh_from_db()
        self.assertEqual(
            self.pending_low_risk_request.status,
            KycRequest.Status.APPROVED,
        )
        self.assertEqual(
            self.pending_low_risk_request.reviewed_by,
            "reviewer@example.com",
        )
        self.assertIsNotNone(self.pending_low_risk_request.reviewed_date)
        created_audit_log = AuditLog.objects.get(record_id=2001)
        self.assertEqual(created_audit_log.action_type, "kyc_request_approved")
        self.assertEqual(created_audit_log.user, "reviewer@example.com")
        self.assertEqual(created_audit_log.record_id, 2001)
        self.assertIsNotNone(created_audit_log.timestamp)
        self.assertIn("status: Pending -> Approved", created_audit_log.details)
        self.assertIn("supervisor: none", created_audit_log.details)
        self.assertIn(
            "notes: Identity documents verified.",
            created_audit_log.details,
        )

    def test_high_risk_approval_without_supervisor_is_refused_and_writes_no_audit_row(
        self,
    ):
        with self.assertRaisesMessage(
            KycRequestBusinessRuleError,
            "A valid supervisor email is required",
        ):
            approve_kyc_request_and_write_audit_log(
                kyc_request_id=2002,
                reviewer_email="reviewer@example.com",
                reviewer_notes="Documents verified.",
                supervisor_email="",
            )

        self.pending_high_risk_request.refresh_from_db()
        self.assertEqual(
            self.pending_high_risk_request.status,
            KycRequest.Status.PENDING,
        )
        self.assertFalse(AuditLog.objects.filter(record_id=2002).exists())

    def test_high_risk_approval_with_invalid_supervisor_is_refused_and_writes_no_audit_row(
        self,
    ):
        with self.assertRaises(KycRequestBusinessRuleError):
            approve_kyc_request_and_write_audit_log(
                kyc_request_id=2002,
                reviewer_email="reviewer@example.com",
                reviewer_notes="Documents verified.",
                supervisor_email="supervisor",
            )

        self.assertFalse(AuditLog.objects.filter(record_id=2002).exists())

    def test_high_risk_approval_with_supervisor_updates_request_and_names_supervisor_in_audit(
        self,
    ):
        approve_kyc_request_and_write_audit_log(
            kyc_request_id=2002,
            reviewer_email="reviewer@example.com",
            reviewer_notes="Escalation reviewed.",
            supervisor_email="supervisor@example.com",
        )

        self.pending_high_risk_request.refresh_from_db()
        self.assertEqual(
            self.pending_high_risk_request.status,
            KycRequest.Status.APPROVED,
        )
        created_audit_log = AuditLog.objects.get(record_id=2002)
        self.assertIn(
            "supervisor: supervisor@example.com",
            created_audit_log.details,
        )

    def test_reject_without_notes_is_refused_and_writes_no_audit_row(self):
        with self.assertRaisesMessage(
            KycRequestBusinessRuleError,
            "Reviewer notes are required",
        ):
            reject_kyc_request_and_write_audit_log(
                kyc_request_id=2001,
                reviewer_email="reviewer@example.com",
                reviewer_notes=" ",
            )

        self.pending_low_risk_request.refresh_from_db()
        self.assertEqual(
            self.pending_low_risk_request.status,
            KycRequest.Status.PENDING,
        )
        self.assertFalse(AuditLog.objects.filter(record_id=2001).exists())

    def test_reject_with_notes_updates_request_and_writes_one_audit_row(self):
        reject_kyc_request_and_write_audit_log(
            kyc_request_id=2001,
            reviewer_email="reviewer@example.com",
            reviewer_notes="Document image is unreadable.",
        )

        self.pending_low_risk_request.refresh_from_db()
        self.assertEqual(
            self.pending_low_risk_request.status,
            KycRequest.Status.REJECTED,
        )
        self.assertEqual(
            self.pending_low_risk_request.reviewed_by,
            "reviewer@example.com",
        )
        self.assertEqual(
            self.pending_low_risk_request.reviewer_notes,
            "Document image is unreadable.",
        )
        self.assertIsNotNone(self.pending_low_risk_request.reviewed_date)
        created_audit_log = AuditLog.objects.get(record_id=2001)
        self.assertEqual(created_audit_log.action_type, "kyc_request_rejected")
        self.assertEqual(created_audit_log.user, "reviewer@example.com")
        self.assertEqual(created_audit_log.record_id, 2001)
        self.assertIsNotNone(created_audit_log.timestamp)
        self.assertIn("status: Pending -> Rejected", created_audit_log.details)
        self.assertIn("supervisor: none", created_audit_log.details)
        self.assertIn(
            "notes: Document image is unreadable.",
            created_audit_log.details,
        )

    def test_reviewing_an_already_reviewed_request_is_refused_and_writes_no_second_audit_row(
        self,
    ):
        approve_kyc_request_and_write_audit_log(
            kyc_request_id=2001,
            reviewer_email="reviewer@example.com",
            reviewer_notes="Approved once.",
            supervisor_email="",
        )

        with self.assertRaisesMessage(
            KycRequestBusinessRuleError,
            "has already been reviewed",
        ):
            reject_kyc_request_and_write_audit_log(
                kyc_request_id=2001,
                reviewer_email="reviewer@example.com",
                reviewer_notes="Attempted second decision.",
            )

        self.assertEqual(AuditLog.objects.filter(record_id=2001).count(), 1)

    def test_pending_filter_matches_risk_band_and_case_insensitive_name_substring(
        self,
    ):
        matching_requests = list_pending_kyc_requests_matching_filters(
            risk_band="high",
            name_search="bOb",
        )

        self.assertEqual(
            [matching_request.kyc_request_id for matching_request in matching_requests],
            [2002],
        )

    def test_history_excludes_pending_requests_filters_status_and_orders_newest_first(
        self,
    ):
        approve_kyc_request_and_write_audit_log(
            kyc_request_id=2001,
            reviewer_email="reviewer@example.com",
            reviewer_notes="Approved.",
            supervisor_email="",
        )
        reject_kyc_request_and_write_audit_log(
            kyc_request_id=2002,
            reviewer_email="reviewer@example.com",
            reviewer_notes="Rejected.",
        )

        rejected_requests = list_reviewed_kyc_requests_matching_status_filter(
            "Rejected"
        )
        all_reviewed_requests = list_reviewed_kyc_requests_matching_status_filter("All")

        self.assertEqual(len(rejected_requests), 1)
        self.assertEqual(rejected_requests[0].kyc_request_id, 2002)
        self.assertEqual(
            [
                reviewed_request.kyc_request_id
                for reviewed_request in all_reviewed_requests
            ],
            [2002, 2001],
        )

    def test_dashboard_counts_pending_approved_today_and_rejected_today(self):
        approve_kyc_request_and_write_audit_log(
            kyc_request_id=2001,
            reviewer_email="reviewer@example.com",
            reviewer_notes="Approved.",
            supervisor_email="",
        )
        reject_kyc_request_and_write_audit_log(
            kyc_request_id=2002,
            reviewer_email="reviewer@example.com",
            reviewer_notes="Rejected.",
        )

        dashboard_totals = count_dashboard_kyc_request_totals()

        self.assertEqual(dashboard_totals["pending_count"], 0)
        self.assertEqual(dashboard_totals["approved_today_count"], 1)
        self.assertEqual(dashboard_totals["rejected_today_count"], 1)


class SeedServicesTests(TestCase):
    def test_seed_is_idempotent_and_creates_expected_users_requests_and_audit_rows(
        self,
    ):
        first_created_request_count = create_seed_users_and_pending_kyc_requests()
        second_created_request_count = create_seed_users_and_pending_kyc_requests()

        self.assertEqual(first_created_request_count, 8)
        self.assertEqual(second_created_request_count, 0)
        self.assertEqual(KycRequest.objects.count(), 8)
        self.assertEqual(AuditLog.objects.filter(action_type="kyc_request_seeded").count(), 8)
        self.assertEqual(
            KycRequest.objects.filter(status=KycRequest.Status.PENDING).count(),
            8,
        )
        self.assertEqual(
            KycRequest.objects.filter(risk_score__gte=1, risk_score__lte=3).count(),
            3,
        )
        self.assertEqual(
            KycRequest.objects.filter(risk_score__gte=4, risk_score__lte=7).count(),
            3,
        )
        self.assertEqual(
            KycRequest.objects.filter(risk_score__gte=8, risk_score__lte=10).count(),
            2,
        )
        self.assertFalse(
            KycRequest.objects.filter(
                submission_date__gt=timezone.localdate()
            ).exists()
        )
        seeded_usernames = set(
            get_user_model()
            .objects.filter(username__in=["reviewer", "supervisor"])
            .values_list("username", flat=True)
        )
        self.assertEqual(seeded_usernames, {"reviewer", "supervisor"})
        self.assertIsNotNone(
            authenticate(username="reviewer", password="reviewer")
        )
        self.assertIsNotNone(
            authenticate(username="supervisor", password="supervisor")
        )


class KycRequestViewsTests(TestCase):
    def setUp(self):
        self.reviewer = get_user_model().objects.create_user(
            username="reviewer-view-test",
            email="reviewer-view-test@example.com",
            password="test-password",
        )
        self.low_risk_request = KycRequest.objects.create(
            kyc_request_id=3001,
            customer_name="Casey Low",
            customer_email="casey.low@example.com",
            risk_score=2,
            submission_date=timezone.localdate(),
        )
        self.high_risk_request = KycRequest.objects.create(
            kyc_request_id=3002,
            customer_name="Riley High",
            customer_email="riley.high@example.com",
            risk_score=8,
            submission_date=timezone.localdate(),
        )

    def test_anonymous_user_is_redirected_to_login_and_login_page_is_public(self):
        dashboard_response = self.client.get(
            reverse("kyc:show_kyc_review_dashboard")
        )
        login_response = self.client.get(reverse("login"))

        self.assertRedirects(
            dashboard_response,
            f"{reverse('login')}?next={reverse('kyc:show_kyc_review_dashboard')}",
        )
        self.assertEqual(login_response.status_code, 200)

    def test_dashboard_shows_totals_pending_requests_filters_and_empty_state(self):
        self.client.force_login(self.reviewer)

        dashboard_response = self.client.get(
            reverse("kyc:show_kyc_review_dashboard"),
            {"risk_band": "Low", "name_search": "casey"},
        )
        empty_dashboard_response = self.client.get(
            reverse("kyc:show_kyc_review_dashboard"),
            {"name_search": "not-a-customer"},
        )

        self.assertContains(dashboard_response, "Pending")
        self.assertContains(dashboard_response, "Casey Low")
        self.assertNotContains(dashboard_response, "Riley High")
        self.assertContains(
            empty_dashboard_response,
            "No pending requests match these filters",
        )

    def test_htmx_dashboard_filter_returns_only_pending_request_results(self):
        self.client.force_login(self.reviewer)

        response = self.client.get(
            reverse("kyc:show_kyc_review_dashboard"),
            {"risk_band": "High"},
            HTTP_HX_REQUEST="true",
        )

        self.assertContains(response, "Riley High")
        self.assertNotContains(response, "<html")

    def test_filter_forms_replace_the_current_url_without_stale_history_entries(
        self,
    ):
        self.client.force_login(self.reviewer)

        dashboard_response = self.client.get(
            reverse("kyc:show_kyc_review_dashboard")
        )
        history_response = self.client.get(
            reverse("kyc:show_reviewed_kyc_request_history")
        )

        self.assertContains(dashboard_response, 'hx-replace-url="true"')
        self.assertNotContains(dashboard_response, "hx-push-url")
        self.assertContains(history_response, 'hx-replace-url="true"')
        self.assertNotContains(history_response, "hx-push-url")

    def test_review_detail_shows_every_request_field_and_risk_badge(self):
        self.client.force_login(self.reviewer)

        response = self.client.get(
            reverse(
                "kyc:show_kyc_request_review_detail",
                args=[self.high_risk_request.kyc_request_id],
            )
        )

        self.assertContains(response, "3002")
        self.assertContains(response, "Riley High")
        self.assertContains(response, "riley.high@example.com")
        self.assertContains(response, "High · 8/10")
        self.assertContains(response, "Pending")
        self.assertContains(response, "Reviewer notes")
        self.assertContains(response, "Reviewed by")
        self.assertContains(response, "Reviewed date")

    def test_low_risk_approval_is_direct_and_returns_to_dashboard_with_success_message(
        self,
    ):
        self.client.force_login(self.reviewer)

        response = self.client.post(
            reverse(
                "kyc:submit_kyc_request_decision",
                args=[self.low_risk_request.kyc_request_id],
            ),
            {
                "decision": "approve",
                "reviewer_notes": "Direct approval.",
                "supervisor_email": "",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("kyc:show_kyc_review_dashboard"))
        self.assertContains(response, "was approved")
        self.low_risk_request.refresh_from_db()
        self.assertEqual(
            self.low_risk_request.status,
            KycRequest.Status.APPROVED,
        )

    def test_high_risk_approval_shows_confirmation_before_writing(self):
        self.client.force_login(self.reviewer)
        decision_url = reverse(
            "kyc:submit_kyc_request_decision",
            args=[self.high_risk_request.kyc_request_id],
        )

        confirmation_response = self.client.post(
            decision_url,
            {
                "decision": "approve",
                "reviewer_notes": "Escalated approval.",
                "supervisor_email": "",
            },
        )

        self.assertContains(
            confirmation_response,
            "Confirm high-risk approval",
        )
        self.high_risk_request.refresh_from_db()
        self.assertEqual(
            self.high_risk_request.status,
            KycRequest.Status.PENDING,
        )
        self.assertFalse(
            AuditLog.objects.filter(
                record_id=self.high_risk_request.kyc_request_id
            ).exists()
        )

        confirmed_response = self.client.post(
            decision_url,
            {
                "decision": "approve",
                "confirmation": "confirmed",
                "reviewer_notes": "Escalated approval.",
                "supervisor_email": "supervisor@example.com",
            },
        )

        self.assertRedirects(
            confirmed_response,
            reverse("kyc:show_kyc_review_dashboard"),
        )
        self.assertEqual(
            AuditLog.objects.filter(
                record_id=self.high_risk_request.kyc_request_id
            ).count(),
            1,
        )

    def test_rejection_requires_notes_and_confirmation_before_writing(self):
        self.client.force_login(self.reviewer)
        decision_url = reverse(
            "kyc:submit_kyc_request_decision",
            args=[self.low_risk_request.kyc_request_id],
        )

        missing_notes_response = self.client.post(
            decision_url,
            {
                "decision": "reject",
                "reviewer_notes": "",
                "supervisor_email": "",
            },
        )
        confirmation_response = self.client.post(
            decision_url,
            {
                "decision": "reject",
                "reviewer_notes": "Identity mismatch.",
                "supervisor_email": "",
            },
        )

        self.assertEqual(missing_notes_response.status_code, 400)
        self.assertContains(
            missing_notes_response,
            "Reviewer notes are required",
            status_code=400,
        )
        self.assertContains(confirmation_response, "Confirm rejection")
        self.assertFalse(
            AuditLog.objects.filter(
                record_id=self.low_risk_request.kyc_request_id
            ).exists()
        )

        confirmed_response = self.client.post(
            decision_url,
            {
                "decision": "reject",
                "confirmation": "confirmed",
                "reviewer_notes": "Identity mismatch.",
                "supervisor_email": "",
            },
        )

        self.assertRedirects(
            confirmed_response,
            reverse("kyc:show_kyc_review_dashboard"),
        )
        self.low_risk_request.refresh_from_db()
        self.assertEqual(
            self.low_risk_request.status,
            KycRequest.Status.REJECTED,
        )

    def test_history_shows_reviewed_requests_newest_first_and_filters_status(self):
        self.client.force_login(self.reviewer)
        approve_kyc_request_and_write_audit_log(
            kyc_request_id=self.low_risk_request.kyc_request_id,
            reviewer_email=self.reviewer.email,
            reviewer_notes="Approved for history.",
            supervisor_email="",
        )
        reject_kyc_request_and_write_audit_log(
            kyc_request_id=self.high_risk_request.kyc_request_id,
            reviewer_email=self.reviewer.email,
            reviewer_notes="Rejected for history.",
        )

        response = self.client.get(
            reverse("kyc:show_reviewed_kyc_request_history"),
            {"status": "Rejected"},
        )

        self.assertContains(response, "Riley High")
        self.assertContains(response, "Rejected")
        self.assertNotContains(response, "Casey Low")


class AdminRegistrationTests(TestCase):
    def test_every_domain_model_is_registered_in_admin(self):
        self.assertTrue(admin.site.is_registered(KycRequest))
        self.assertTrue(admin.site.is_registered(AuditLog))
