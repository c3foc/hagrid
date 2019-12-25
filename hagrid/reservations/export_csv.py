import csv
import io
import logging

from hagrid.products.models import Variation
from .models import Reservation

logger = logging.getLogger(__name__)


def write_reservation(reservation: Reservation, writer):
    writer.writerow(['Next Reservation', str(reservation.id), str(reservation.team_name),
        str(reservation.contact_name), str(reservation.contact_mail), str(reservation.contact_dect),
        str(reservation.state), str(reservation.packing_mode),
        "total of reservation: [EUR] ", "{:20,.2f}".format(reservation.price),
        str(reservation.comment)])
    for part in reservation.parts.all():
        writer.writerow(['Next Part', str(part.title), "total of part: [EUR] ",
            "{:20,.2f}".format(part.price)])
        for position in part.positions.all():
            variation: Variation = position.variation
            writer.writerow(['Next position', 'Item:', str(variation), 'Amount: ', str(position.amount),
                'Single price: [EUR] ', "{:20,.2f}".format(variation.product.price), 'aggregated price: [EUR]',
                "{:20,.2f}".format(position.price)])
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
