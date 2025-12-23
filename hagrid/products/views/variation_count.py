from datetime import datetime, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.views import login_required
from django.db.models import Q
from django.http.response import Http404
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from hagrid.operations.models import EventTime

from ..models import (
    Product,
    Size,
    SizeGroup,
    StoreSettings,
    Variation,
    VariationCountAccessCode,
    VariationCountEvent,
)


class VariationCountForm(forms.ModelForm):
    def __init__(self, *args, count_required=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["count"].widget = forms.NumberInput()
        self.fields["count"].required = count_required

    class Meta:
        model = VariationCountEvent
        exclude = ["datetime", "variation", "comment", "name"]


class VariationCountCommonForm(forms.Form):
    name = forms.CharField(
        label="Nickname",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "optional, see tutorial",
                "data-synclocalstorage": "nickname",
            }
        ),
    )
    comment = forms.CharField(
        label="Comment",
        max_length=250,
        required=False,
        widget=forms.Textarea(attrs={"rows": "2"}),
    )
    action = forms.ChoiceField(
        choices=[
            ("save", "Save"),
            ("need_to_go", "Gotta go, sorry!"),
            ("cannot_find", "Can't find/access it"),
            ("something_wrong", "Something is not right"),
            ("other", "Other"),
        ]
    )


@require_http_methods(["POST", "GET"])
def variation_count(request, code, variation_id=None):
    if not StoreSettings.objects.first().counting_enabled:
        messages.add_message(
            self.request, messages.ERROR, "We are not counting items at the moment."
        )
        return redirect("dashboard")

    access_code = get_object_or_404(VariationCountAccessCode, code=code, disabled=False)

    if access_code.as_queue:
        if not variation_id:
            form = forms.Form(request.POST or None)

            event_time = EventTime()

            priorities = []
            available_variations = access_code.variations.filter(
                ~Q(count=0)
                & (
                    Q(count_reserved_until__isnull=True)
                    | Q(count_reserved_until__lt=datetime.now())
                )
                & (
                    Q(count_disabled_until__isnull=True)
                    | Q(count_disabled_until__lt=datetime.now())
                )
            )
            if not available_variations:
                messages.add_message(
                    request,
                    messages.INFO,
                    "Nothing to count at the moment, please come back later.",
                )
                return redirect("dashboard")
            else:
                for variation in available_variations:
                    priorities.append(
                        {
                            "variation": variation,
                            **variation.get_count_priority(event_time),
                        }
                    )

                priorities = sorted(priorities, key=lambda s: s["total"], reverse=True)

                if request.POST and form.is_valid():
                    top_prio = priorities[0]
                    variation = top_prio["variation"]
                    variation.count_reserved_until = datetime.now() + timedelta(
                        minutes=15
                    )
                    variation.save()

                    # assign a variation and redirect
                    return redirect("variation_count", code, variation.id)

                important = sum(map(lambda p: int(p["total"] >= 0.5), priorities), 0)

                return render(
                    request,
                    "variation_count_queue.html",
                    {
                        "form": form,
                        "total_variations": len(priorities),
                        "high_prio_variations": important,
                    },
                )

        try:
            variations = [access_code.variations.get(id=variation_id)]
        except Variation.DoesNotExist:
            raise Http404()

    elif variation_id:
        raise Http404()
    else:
        variations = list(access_code.variations)

    common_form = VariationCountCommonForm(request.POST or None)

    items = [
        {
            "variation": variation,
            "form": VariationCountForm(
                request.POST or None,
                prefix="variation_{}".format(variation.id),
                count_required=bool(variation_id),
            ),
        }
        for variation in variations
    ]

    common_name = []
    products_used = list(Product.objects.filter(variations__in=variations).distinct())
    product_column = len(products_used) > 1
    if not product_column:
        common_name.append(str(products_used[0]))

    sizegroups_used = list(
        SizeGroup.objects.filter(sizes__variations__in=variations).distinct()
    )
    sizegroup_column = len(sizegroups_used) > 1
    if not sizegroup_column:
        common_name.append(str(sizegroups_used[0]))

    sizes_used = list(Size.objects.filter(variations__in=variations).distinct())
    size_column = len(sizes_used) > 1
    if not size_column:
        common_name.append(str(sizes_used[0]))

    if request.POST:
        now = datetime.now()

        if common_form.is_valid() and common_form.cleaned_data["action"] != "save":
            if variation_id:
                variation = Variation.objects.get(id=variation_id)
                common_form.cleaned_data["action"]
                variation.count_disabled_reason = common_form.cleaned_data["action"]
                if variation.count_disabled_reason in (
                    "cannot_find",
                    "something_wrong",
                    "other",
                ):
                    # let's skip this for 15 minutes
                    variation.count_disabled_until = now + timedelta(minutes=15)
                else:
                    variation.count_disabled_until = None
                variation.count_reserved_until = None
                variation.save()
                messages.add_message(
                    request,
                    messages.INFO,
                    "Thank you for telling us. You can still count something if you want!",
                )
                return redirect("variation_count", code)

        elif common_form.is_valid() and all(map(lambda i: i["form"].is_valid(), items)):
            total = 0
            items_changed = 0

            for item in items:
                form = item["form"]
                variation = item["variation"]
                count = form.cleaned_data["count"]
                if count is not None:
                    variation.count = count
                    variation.count_reserved_until = None
                    variation.count_disabled_until = None
                    variation.count_disabled_reason = None
                    variation.counted_at = now
                    variation.count_prio_bumped = False
                    variation.save()
                    total += count
                    items_changed += 1

                    VariationCountEvent(
                        count=count,
                        variation=variation,
                        comment=common_form.cleaned_data["comment"],
                        name=common_form.cleaned_data["name"],
                    ).save()

            if access_code.as_queue:
                messages.add_message(
                    request,
                    messages.INFO,
                    "Thank you for counting this item. You can do another if you want!",
                )
                return redirect("variation_count", code)
            return redirect(
                reverse("variation_count_success")
                + f"?total={total}&items_changed={items_changed}"
            )

    if variation_id:
        return render(
            request,
            "variation_count_from_queue.html",
            {
                "access_code": access_code,
                "variation": items[0]["variation"],
                "form": items[0]["form"],
                "common_form": common_form,
            },
        )

    return render(
        request,
        "variation_count.html",
        {
            "product_column": product_column,
            "sizegroup_column": sizegroup_column,
            "size_column": size_column,
            "column_count": product_column + sizegroup_column + size_column,
            "common_name": " / ".join(common_name),
            "access_code": access_code,
            "items": items,
            "common_form": common_form,
        },
    )


@require_GET
def variation_count_success(request):
    try:
        total = int(request.GET.get("total"))
        items_changed = int(request.GET.get("items_changed"))
    except (ValueError, TypeError) as _e:
        raise Http404()

    return render(
        request,
        "variation_count_success.html",
        {
            "total": total,
            "items_changed": items_changed,
        },
    )


class VariationBumpForm(forms.Form):
    variation = forms.IntegerField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices=[
            ("bump", "Bump"),
            ("unbump", "Unbump"),
            ("clear_disabled", "Clear disabled"),
        ]
    )


@login_required()
@require_http_methods(["POST", "GET"])
def variation_count_overview(request):
    event_time = EventTime()

    priorities = []
    for variation in Variation.objects.all():
        prefix = f"variation-{variation.id}"
        form = (
            VariationBumpForm(request.POST, prefix=prefix)
            if request.POST
            else VariationBumpForm(prefix=prefix, initial={"variation": variation.id})
        )

        priorities.append(
            {
                "variation": variation,
                **variation.get_count_priority(event_time),
                "form": form,
            }
        )

    if request.POST:
        for priority in priorities:
            form = priority["form"]
            variation = priority["variation"]
            if form.is_valid() and variation.id == form.cleaned_data["variation"]:
                if form.cleaned_data["action"] == "bump":
                    variation.count_prio_bumped = True
                elif form.cleaned_data["action"] == "unbump":
                    variation.count_prio_bumped = False
                elif form.cleaned_data["action"] == "clear_disabled":
                    variation.count_disabled_reason = None
                    variation.count_disabled_until = None
                variation.save()
                messages.info(
                    request,
                    str(variation)
                    + (" bumped" if variation.count_prio_bumped else " unbumped"),
                )
                return redirect("variation_count_overview")

    priorities = sorted(priorities, key=lambda s: s["total"], reverse=True)

    context = {"priorities": priorities}
    return render(request, "variation_count_overview.html", context)


@login_required()
@require_GET
def variation_count_log(request):
    event_time = EventTime()
    now = event_time.datetime_to_event_time(timezone.now())
    events = VariationCountEvent.objects.order_by("-datetime").all()
    context = {
        "items": [
            {
                "event": event,
                "age": now - event_time.datetime_to_event_time(event.datetime),
            }
            for event in events
        ]
    }
    return render(request, "variation_count_log.html", context)
