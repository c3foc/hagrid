from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.db.models import Sum

from hagrid.products.models import Size, SizeGroup, StoreSettings, Product, ProductGroup
from hagrid.products.tables import SizeTable

from ..models import Reservation, ReservationPart, ReservationPosition
from hagrid.reservations import emails


def require_reservation_state(required_state, superuser_bypass=False):
    def decorator(func):
        def decorated_function(self, request, *args, **kwargs):
            reservation = get_object_or_404(Reservation, secret=kwargs["secret"])
            if reservation.state == required_state:
                return func(self, request, *args, **kwargs)
            if superuser_bypass and request.user.is_superuser:
                if request.method == "GET":
                    messages.add_message(
                        request,
                        messages.WARNING,
                        "You are allowed on this page only because you are a superuser.",
                    )
                return func(self, request, *args, **kwargs)
            messages.add_message(request, messages.ERROR, "This action is forbidden.")
            return redirect("reservationdetail", secret=kwargs["secret"])

        return decorated_function

    return decorator


class ReservationCommentForm(forms.ModelForm):
    def __init__(self, *args, editable=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["comment"].widget.attrs["rows"] = 2
        if not editable:
            for field in self.fields.values():
                field.disabled = True

    class Meta:
        model = Reservation
        fields = ["comment", "packing_mode"]


class ReservationDetailView(TemplateView):
    template_name = "reservationdetail.html"

    def get_form(self, request, reservation):
        return ReservationCommentForm(
            request.POST or None,
            instance=reservation,
            editable=reservation.state == Reservation.STATE_EDITABLE
            or request.user.is_superuser,
        )

    def get(self, request, secret):
        reservation = get_object_or_404(Reservation, secret=secret)
        return render(
            request,
            self.template_name,
            {
                "reservation": reservation,
                "comment_form": self.get_form(request, reservation),
            },
        )

    @require_reservation_state(Reservation.STATE_EDITABLE, superuser_bypass=True)
    def post(self, request, secret):
        reservation = get_object_or_404(Reservation, secret=secret)
        form = self.get_form(request, reservation)
        if form.is_valid():
            form.save()
            messages.add_message(
                self.request, messages.SUCCESS, "Information has been updated."
            )
            return redirect("reservationdetail", secret=secret)
        return render(
            request,
            self.template_name,
            {
                "reservation": reservation,
                "comment_form": self.get_form(request, reservation),
            },
        )


class ReservationSubmitView(View):
    template_name = "reservationsubmit.html"

    @require_reservation_state(Reservation.STATE_EDITABLE)
    def get(self, request, secret):
        return render(
            request,
            self.template_name,
            {
                "reservation": get_object_or_404(Reservation, secret=secret),
                "form": forms.Form(),
            },
        )

    @require_reservation_state(Reservation.STATE_EDITABLE)
    def post(self, request, secret):
        form = forms.Form(request.POST)
        reservation = get_object_or_404(Reservation, secret=secret)
        if form.is_valid():
            reservation.state = Reservation.STATE_SUBMITTED
            reservation.save()
            emails.send_reservation_submitted_mail(reservation)
            return redirect("reservationdetail", secret=secret)
        return self.get(request, secret)


class ReservationPartDeleteView(View):
    @require_reservation_state(Reservation.STATE_EDITABLE, superuser_bypass=True)
    def post(self, request, secret, part_id):
        form = forms.Form(request.POST)
        part = get_object_or_404(ReservationPart, id=part_id)
        if form.is_valid():
            part.delete()
            messages.add_message(
                self.request, messages.SUCCESS, "{} has been deleted.".format(str(part))
            )
            return redirect("reservationdetail", secret=secret)
        return render(
            request, "reservationpartdelete.html", {"part": part, "form": forms.Form()}
        )

    @require_reservation_state(Reservation.STATE_EDITABLE, superuser_bypass=True)
    def get(self, request, secret, part_id):
        part = get_object_or_404(ReservationPart, id=part_id)
        return render(
            request, "reservationpartdelete.html", {"part": part, "form": forms.Form()}
        )


class ReservationPartCreateView(View):
    @require_reservation_state(Reservation.STATE_EDITABLE, superuser_bypass=True)
    def post(self, request, secret):
        reservation = get_object_or_404(Reservation, secret=secret)
        number_of_parts = reservation.parts.count()
        form = forms.Form(request.POST)
        if form.is_valid():
            new_part = ReservationPart.objects.create(
                reservation=reservation,
                title="{} #{}".format(reservation.team_name, number_of_parts + 1),
            )
            return redirect("reservationpartdetail", secret=secret, part_id=new_part.id)
        # return redirect('reservationdetail', secret=secret)


def amount_reserved(variation):
    return (
        ReservationPosition.objects.filter(variation=variation).aggregate(
            reserved=Sum("amount")
        )["reserved"]
        or 0
    )


class ReservationPositionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        disable_amount = kwargs.pop("disable_amount", False)
        super().__init__(*args, **kwargs)
        self.fields["variation"].widget = forms.NumberInput()
        variation = self.initial["variation"]
        old_amount = self.initial["amount"]
        self.max_amount = max(
            0, variation.initial_amount - amount_reserved(variation) + old_amount
        )
        self.fields["amount"].widget.attrs.update(
            {
                "style": "width: 7ch;",
                "class": "variationcounthighlight",
                "max": self.max_amount,
            }
        )
        self.fields["amount"].disabled = disable_amount

        if self.max_amount == 0:
            self.fields["amount"].widget.attrs.update({"readonly": ""})

    def clean(self):
        cleaned_data = super().clean()
        variation = cleaned_data["variation"]
        old_amount = self.initial["amount"]
        new_amount = max(0, cleaned_data.get("amount", 0))
        max_amount = max(
            0, variation.initial_amount - amount_reserved(variation) + old_amount
        )
        if variation and new_amount:
            if new_amount > max_amount:
                msg = (
                    "No {variation} available."
                    if max_amount == 0
                    else "Only {amount} {variation} available."
                )
                msg += " Choose {amount} at most."
                self.add_error(
                    "amount", msg.format(amount=max_amount, variation=str(variation))
                )
                if "readonly" in self.fields["amount"].widget.attrs:
                    del self.fields["amount"].widget.attrs["readonly"]

    class Meta:
        model = ReservationPosition
        exclude = ["part"]


class ReservationPartTitleForm(forms.ModelForm):
    class Meta:
        model = ReservationPart
        fields = ["title"]


class ReservationPartDetailView(View):
    @require_reservation_state(Reservation.STATE_EDITABLE, superuser_bypass=True)
    def post(self, request, secret, part_id):
        reservation_part = get_object_or_404(ReservationPart, id=part_id)
        variation_tables, variation_forms = self.get_variation_tables_and_forms(
            request, reservation_part
        )
        part_form = ReservationPartTitleForm(request.POST, instance=reservation_part)
        if part_form.is_valid():
            part_form.save()
        else:
            return render(
                request,
                "reservationpartdetail.html",
                {
                    "variation_tables": variation_tables,
                    "part_form": ReservationPartTitleForm(instance=reservation_part),
                },
            )
        for form in variation_forms:
            if form.is_valid():
                if form.cleaned_data["amount"]:
                    position, created = ReservationPosition.objects.get_or_create(
                        part=reservation_part,
                        variation=form.cleaned_data["variation"],
                    )
                    position.amount = form.cleaned_data["amount"]
                    position.save()
                else:
                    ReservationPosition.objects.filter(
                        part=reservation_part, variation=form.cleaned_data["variation"]
                    ).delete()
            else:
                return render(
                    request,
                    "reservationpartdetail.html",
                    {
                        "variation_tables": variation_tables,
                        "part_form": ReservationPartTitleForm(
                            instance=reservation_part
                        ),
                    },
                )
        messages.add_message(
            self.request,
            messages.SUCCESS,
            "Part {} has been saved.".format(reservation_part.title),
        )
        return redirect("reservationdetail", secret=secret)

    @require_reservation_state(Reservation.STATE_EDITABLE, superuser_bypass=True)
    def get(self, request, secret, part_id):
        reservation_part = get_object_or_404(ReservationPart, id=part_id)
        variation_tables, variation_forms = self.get_variation_tables_and_forms(
            request, reservation_part
        )
        return render(
            request,
            "reservationpartdetail.html",
            {
                "variation_tables": variation_tables,
                "part_form": ReservationPartTitleForm(instance=reservation_part),
                "unoffered_product_groups": ProductGroup.objects.all().filter(
                    offer_in_reservations=False
                ),
            },
        )

    def get_variation_tables_and_forms(self, request, part):
        forms = []

        part_positions = ReservationPosition.objects.filter(part=part)

        def render_form(form):
            return render_to_string(
                "variation_picker_box.html", context={"form": form}, request=request
            )

        def render_variation_form(variation):
            prefix = "{}".format(variation.id)
            disabled = not variation.product.product_group.offer_in_reservations
            try:
                amount = part_positions.get(variation=variation).amount
                disabled = disabled and amount == 0
            except ReservationPosition.DoesNotExist:
                amount = 0
            if request.POST:
                form = ReservationPositionForm(
                    request.POST,
                    disable_amount=disabled,
                    prefix=prefix,
                    initial={
                        "amount": amount,
                        "variation": variation,
                        "part": part,
                    },
                )
                form.full_clean()
            else:
                form = ReservationPositionForm(
                    prefix=prefix,
                    disable_amount=disabled,
                    initial={
                        "amount": amount,
                        "variation": variation,
                        "part": part,
                    },
                )
            forms.append(form)
            return render_form(form)

        tables = [
            SizeTable(
                sizegroup,
                render_variation=render_variation_form,
                products_queryset=Product.objects.all().select_related("product_group"),
            )
            for sizegroup in SizeGroup.objects.all().prefetch_related("sizes")
        ]
        return tables, forms


class ReservationApplicationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            "team_name",
            "contact_name",
            "contact_mail",
            "contact_dect",
            "comment",
        ]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 2}),
        }


class ReservationApplicationView(FormView):
    template_name = "reservationapplication.html"
    form_class = ReservationApplicationForm

    def form_valid(self, form):
        # Create Reservation
        if not StoreSettings.objects.first().reservations_enabled:
            messages.add_message(
                self.request, messages.ERROR, "Reservations are disabled."
            )
            return redirect("reservationapplication")
        new_reservation = form.save()
        new_reservation.secret = get_random_string(length=16)
        while Reservation.objects.filter(secret=new_reservation.secret).exists():
            new_reservation.secret = get_random_string(length=16)
        new_reservation.save()

        # Send email and redirect
        emails.send_new_reservation_mail(new_reservation)
        messages.add_message(
            self.request, messages.SUCCESS, "Your application was received."
        )
        messages.add_message(
            self.request,
            messages.WARNING,
            "You must save the URL of this page to access your reservation later.",
        )
        return redirect("reservationdetail", secret=new_reservation.secret)
