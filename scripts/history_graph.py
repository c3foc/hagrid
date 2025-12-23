import datetime

from scripts.data import events_37c3, variations_37c3

OPENING_HOURS = [
    (datetime.datetime(2023, 12, 27, 13, 0), datetime.datetime(2023, 12, 28, 0, 0)),
    (datetime.datetime(2023, 12, 28, 12, 0), datetime.datetime(2023, 12, 29, 0, 0)),
    (datetime.datetime(2023, 12, 29, 12, 0), datetime.datetime(2023, 12, 29, 21, 30)),
]

# localize opening hours to Europe/Berlin
import pytz

TZ_BERLIN = pytz.timezone('Europe/Berlin')
OPENING_HOURS = [(start.replace(tzinfo=TZ_BERLIN),
                  end.replace(tzinfo=TZ_BERLIN))
                 for start, end in OPENING_HOURS]


def intersect_with_opening_hours(start, end):
    timeslots = []
    # for every opening hour, intersect start to end with opening hours and add to timeslots
    for opening_start, opening_end in OPENING_HOURS:
        if start < opening_end and end > opening_start:
            timeslots.append((max(start, opening_start), min(end, opening_end)))
    return timeslots


def show_plot():
    import plotly.figure_factory as ff

    dataframe = []

    for variation_id, variation_name in variations_37c3.items():
        if "37c3" in variation_name.lower():
            last_time = datetime.datetime(2023, 12, 27, 13, 0, tzinfo=TZ_BERLIN)
        elif any(term in variation_name.lower() for term in ["towel", "hipbag"]):
            continue
            last_time = datetime.datetime(2023, 12, 28, 12, 0, tzinfo=TZ_BERLIN)
        else:
            continue
            last_time = datetime.datetime(2023, 12, 28, 16, 0, tzinfo=TZ_BERLIN)
        last_state = None
        for event in sorted(events_37c3, key=lambda e: e['datetime']):
            if event['variation_id'] == variation_id:
                start = last_time
                end = event['datetime']
                last_time = end
                last_state = event['new_state']

                # add timeslots to dataframe
                for timeslot_start, timeslot_end in intersect_with_opening_hours(start, end):
                    dataframe.append(dict(Task=variation_name, Start=timeslot_start, Finish=timeslot_end,
                                          State=event['old_state']))

        if last_state:
            start = last_time
            end = datetime.datetime(2023, 12, 29, 21, 30, tzinfo=TZ_BERLIN)
            for timeslot_start, timeslot_end in intersect_with_opening_hours(start, end):
                dataframe.append(
                    dict(Task=variation_name, Start=timeslot_start, Finish=timeslot_end, State=last_state))

    colors = {
        'available': 'rgb(50, 250, 50)',
        'few available': 'rgb(250, 250, 50)',
        'sold out': 'rgb(250, 50, 50)',
    }

    # fixup dataframe to only have naive datetimes in TZ_BERLIN
    for row in dataframe:
        row['Start'] = row['Start'].astimezone(TZ_BERLIN).replace(tzinfo=None)
        row['Finish'] = row['Finish'].astimezone(TZ_BERLIN).replace(tzinfo=None)

    # sort dataframe by task name
    dataframe = sorted(dataframe, key=lambda row: row['Task'])
    fig = ff.create_gantt(dataframe, title="Merchandise availability", colors=colors, index_col='State', show_colorbar=True,
                          group_tasks=True, height=1000, width=1600, showgrid_x=True, showgrid_y=True)
    fig.show()


def write_available_time_csv():
    cumulative_available_times = {}
    for variation_id, variation_name in variations_37c3.items():
        if "37c3" not in variation_name.lower():
            continue
        last_time = datetime.datetime(2023, 12, 27, 13, 0, tzinfo=TZ_BERLIN)
        dataframe = []
        last_state = None
        for event in sorted(events_37c3, key=lambda e: e['datetime']):
            if event['variation_id'] == variation_id:
                start = last_time
                end = event['datetime']
                last_time = end
                last_state = event['new_state']

                # add timeslots to dataframe
                for timeslot_start, timeslot_end in intersect_with_opening_hours(start, end):
                    dataframe.append(dict(Task=variation_name, Start=timeslot_start, Finish=timeslot_end,
                                          State=event['old_state']))
        if last_state:
            start = last_time
            end = datetime.datetime(2023, 12, 29, 21, 30, tzinfo=TZ_BERLIN)
            for timeslot_start, timeslot_end in intersect_with_opening_hours(start, end):
                dataframe.append(
                    dict(Task=variation_name, Start=timeslot_start, Finish=timeslot_end, State=last_state))
        cumulative_available_times[variation_name] = sum([
            (e['Finish'] - e['Start'])/datetime.timedelta(hours=1) for e in dataframe if e['State'] == 'available'
        ], start=0.0)

        import csv
        with open('37c3-availability-times.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',',
                                    quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for variation_name, time in cumulative_available_times.items():
                writer.writerow([variation_name, time])


if __name__ == '__main__':
    write_available_time_csv()
    show_plot()
