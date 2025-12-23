import csv
import io
import logging

from hagrid.products.models import Variation
from .models import Reservation

logger = logging.getLogger(__name__)


def write_reservation(reservation: Reservation, writer):
    writer.writerow(
        [
            "team name",
            "part name",
            "position idstate",
            "price",
            "product name",
            "size group",
            "size",
            "full product desciption",
        ]
    )
    for part in reservation.parts.all():
        for position in part.positions.all():
            variation: Variation = position.variation
            for i in range(position.amount):
                writer.writerow(
                    [
                        str(reservation.team_name),
                        str(part.title),
                        str(position.id) + "-" + str(i),
                        str(reservation.contact_name),
                        str(reservation.state),
                        str(variation.product.price),
                        str(variation.product.name),
                        str(variation.size.group.name),
                        str(variation.size.name),
                        str(variation.product.name)
                        + " "
                        + str(variation.size.group.name)
                        + " "
                        + str(variation.size.name),
                    ]
                )
    writer.writerow([])


def generate_reservation_csv(reservations):
    """
    This method returns the requested reservations as csv file bytes.

    Parameters
    ----------
    reservations: [Reservation]
        An array containing the reservations that should be exported.
    """
    data_buffer = (
        io.StringIO()
    )  # unfortunately the fast cStringIO isn't avaiable anymore
    writer = csv.writer(data_buffer)
    for reservation in reservations:
        write_reservation(reservation, writer)
    data_bytes = data_buffer.getvalue()
    data_buffer.close()
    return data_bytes
