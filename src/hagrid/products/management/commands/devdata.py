import datetime
import itertools
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction

from hagrid.operations.models import OpenStatus
from hagrid.products.models import (
    Design,
    DesignVariation,
    Event,
    Price,
    Product,
    ProductCategory,
    Size,
    SizeScale,
    SizeVariation,
    StoreSettings,
)

DASHBOARD_TEXT = """<div>
  <h2>Merch desk opening hours</h2>
  <ul>
    <li>Day 1: 13:00 - 24:00 <strong>Preorder pickup only</strong></li>
    <li>Day 2: 12:00 - 24:00</li>
    <li>Day 3: 12:00 - 22:00</li>
    <li>Day 4: closed</li>
  </ul>

  <p>Angel shirts are distributed by the Angel Shirt desk and/or Heaven, not FOC. Please check for annoucements in Engelsystem.</p>
</div>

%open_status%

<div>
  <h2>Contact</h2>
  <p>
    Check <a href="https://c3foc.net">c3foc.net</a> for updates on opening times and item availability.
    For any questions, e.g. regarding the pickup of your preorder, come by the FOC desk or
    call <a href="tel:1362">1FOC (1362 via DECT)</a>.
  </p>

  <p>Happy shopping!</p>
</div>"""


def create_objects():
    admin_user = get_user_model().objects.create(
        username="admin",
    )
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.password = make_password("admin")
    admin_user.save()

    category_garment = ProductCategory.objects.create(name="Garment")
    category_nongarment = ProductCategory.objects.create(name="NonGarment")

    sizes_SML = SizeScale.objects.create(name="SML")
    for s in ["2XS", "XS", "S", "M", "L", "XL"] + [f"{i}XL" for i in range(2, 9)]:
        Size.objects.create(name=s, scale=sizes_SML)
    sizes_onesize = SizeScale.objects.create(name="onesize")
    Size.objects.create(name="-", scale=sizes_onesize)

    hoodie = Product.objects.create(
        category=category_garment,
        name="Hoodie",
        size_scale=sizes_SML,
    )
    shirt_straight = Product.objects.create(
        category=category_garment,
        name="T-Shirt (straight)",
        size_scale=sizes_SML,
    )
    stickers = Product.objects.create(
        category=category_nongarment,
        name="Stickers",
        size_scale=sizes_onesize,
    )

    c48 = Event.objects.create(
        name="48C3",
        day_1=datetime.date(2024, 12, 27),
        last_day=datetime.date(2024, 12, 30),
    )
    blue_rocket = Design.objects.create(
        event=c48,
        name="Blue Rocket",
    )
    black_rocket = Design.objects.create(
        event=c48,
        name="Black Rocket",
    )
    c49 = Event.objects.create(
        name="49C3",
        day_1=datetime.date(2025, 12, 27),
        last_day=datetime.date(2025, 12, 30),
    )
    red_sparkle = Design.objects.create(
        event=c49,
        name="Red Sparkle",
    )
    green_sparkle = Design.objects.create(
        event=c49,
        name="Green Sparkle",
    )
    black_stars = Design.objects.create(
        event=c49,
        name="Black Stars",
    )

    for product, design in itertools.product(
        [hoodie, shirt_straight], [blue_rocket, black_rocket, red_sparkle, green_sparkle]
    ):
        d = DesignVariation.objects.create(
            product=product,
            design=design,
        )
        for i, (size, amount) in enumerate(
            zip(
                sizes_SML.sizes.all(),
                [
                    5,  # 2XS
                    15,  # XS
                    40,  # S
                    140,  # M
                    200,  # L
                    180,  # XL
                    90,  # 2XL
                    20,  # 3XL
                    10,
                    10,
                    3,
                    3,
                    3,  # 4 to 8 XL
                ],
            )
        ):
            if product is hoodie or 1 <= i <= 9:  # shirts only XS to 5XL
                preorder_rate = 0.4 - 0.2 * amount / 200  # 40% to 20%
                SizeVariation.objects.create(
                    design_variation=d,
                    size=size,
                    availability=SizeVariation.STATE_MANY_AVAILABLE,
                    count=amount,
                    amount_initial=amount,
                    amount_preordered=int(amount * preorder_rate),
                )

    black_star_stickers = DesignVariation.objects.create(
        product=stickers,
        design=black_stars,
    )
    SizeVariation.objects.create(
        design_variation=black_star_stickers,
        size=sizes_onesize.sizes.first(),
        count=450,
        amount_initial=500,
        amount_preordered=0,
    )

    os = OpenStatus.objects.create(
        datetime=datetime.datetime(2025, 12, 28, tzinfo=ZoneInfo("Europe/Berlin")),
        mode=OpenStatus.Mode.OPEN,
        event=c49,
    )
    os.selling_items_from.set([c48, c49])
    OpenStatus.objects.create(
        datetime=datetime.datetime(2050, 12, 28, tzinfo=ZoneInfo("Europe/Berlin")),
        mode=OpenStatus.Mode.CLOSED,
        event=c49,
    )

    for event in [c48, c49]:
        Price.objects.create(
            valid_at=event, valid_for_products_from_event=event, product=hoodie, amount=45
        )
        Price.objects.create(
            valid_at=event,
            valid_for_products_from_event=event,
            product=shirt_straight,
            amount=25,
        )
    Price.objects.create(
        valid_at=c49,
        valid_for_products_from_event=c48,
        product=shirt_straight,
        amount=10,
    )

    StoreSettings.objects.create(
        dashboard_text=DASHBOARD_TEXT,
        reservations_enabled=True,
        reservations_link_in_navbar=True,
        counting_enabled=True,
    )


class Command(BaseCommand):
    help = "Load some data for development"

    def handle(self, *args, **options):
        if get_user_model().objects.exists():
            self.stdout.write("WARNING! User objects already exist in your database.")
            if input("Are you sure you want to continue? (yes/no) ") != "yes":
                self.stdout.write("Aborting...")
                return
        with transaction.atomic():
            create_objects()
        self.stdout.write(self.style.SUCCESS("Done."))
