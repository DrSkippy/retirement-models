from datetime import datetime
from datetime import timedelta

def create_datetime_sequence(start_date, end_date):
    """
    Create a sequence of datetime objects from start_date to end_date with a specified step in days.
    
    :param start_date: The starting date as a datetime object.
    :param end_date: The ending date as a datetime object.
    :param step_days: The number of days to increment for each step in the sequence.
    :return: A list of datetime objects.
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    dt = timedelta(days=32)

    current_date = start_date
    date_sequence = []

    while current_date <= end_date:
        date_sequence.append(current_date)
        current_date += dt
        current_date = current_date.replace(day=1)

    return date_sequence