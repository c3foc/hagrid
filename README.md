
# hagrid

This is a software for merchandise sale at Chaos Communication Congress.

### Features

* Configure Products (Hoodie, Shirt, Zipper, ...) in various sizes (Straight M, ...).
* Display product availability in a public dashboard.
* Allow teams to apply for and edit their reservations.
* Let c3foc manage reservations.

### Setup

For now, this is a pretty standard Django Application developed with python3.7. Use `pip install -U -r requirements.txt` in a seperate python environment to install the dependencies. Make sure to adjust the (security related) settings in `settings.py` for use in production.

### Todo List

* Limit reservation to intial amount
* add a note to the whole reservation
* image/price gallery
* email notifications und SIP/DECT notifications
* Size, Sizegroup and Product reodering
