
# hagrid

This is a software for merchandise sale at Chaos Communication Congress.

### Features

* Configure Products (Hoodie, Shirt, Zipper, ...) in various sizes (Fitted M, Unisex 5XL, ...).
* Display product availability in a public dashboard.
* Allow teams to apply for and edit their reservations.
* Let c3foc manage reservations.

### Design principles

* All Functionality should not require javascript to be enabled in the user's browser. Javascript is used for bootstrap's responsive menus on small screens and for some cosmetics.

### Setup

For now, this is a pretty standard Django Application developed with python3.7. Use `pip install -U -r requirements.txt` in a seperate python environment to install the dependencies. Make sure to adjust the (security related) settings in `settings.py` for use in production.

All configuration views are only visible to logged in superusers. Using `./manage.py createsuperuser`, create a new superuser and login on the webpage.

### Todo List

* add a note to the whole reservation
* image/price gallery
* email notifications und SIP/DECT notifications
* Size, Sizegroup and Product reodering and editing outside django admin
* Own Login/Logout/Usermanagement
