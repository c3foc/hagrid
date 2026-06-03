import csv
import io
import logging

from ..products.models import SizeVariation
from .models import Reservation

logger = logging.getLogger(__name__)


def write_reservation(reservation: Reservation, writer):
    writer.writerow([
        "event",
        "team name",
        "state",
        "contact name",
        "part name",
        "position and number",
        "price",
        "item",
    ])
    for part in reservation.parts.all():
        for position in part.positions.all():
            variation: SizeVariation = position.variation
            for i in range(position.amount):
                writer.writerow([
                    str(reservation.event),
                    str(reservation.team_name),
                    str(reservation.state),
                    str(reservation.contact_name),
                    str(part.title),
                    str(position.id) + "-" + str(i),
                    str(variation.get_price_at(reservation.event)),
                    str(variation),
                ])
    writer.writerow([])


def generate_reservation_csv(reservations):
    """
    This method returns the requested reservations as csv file bytes.

    Parameters
    ----------
    reservations: [Reservation]
        An array containing the reservations that should be exported.
    """
    data_buffer = io.StringIO()  # unfortunately the fast cStringIO isn't avaiable anymore
    writer = csv.writer(data_buffer)
    for reservation in reservations:
        write_reservation(reservation, writer)
    data_bytes = data_buffer.getvalue()
    data_buffer.close()
    return data_bytes
