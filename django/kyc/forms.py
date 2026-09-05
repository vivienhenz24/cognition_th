from django import forms


class KycRequestDecisionForm(forms.Form):
    reviewer_notes = forms.CharField(
        required=False,
        label="Reviewer notes",
        widget=forms.Textarea(
            attrs={
                "placeholder": "Record the evidence and reasoning for this decision.",
            }
        ),
    )
    supervisor_email = forms.CharField(
        required=False,
        label="Supervisor email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "supervisor@example.com",
            }
        ),
    )
