
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

For now, this is a pretty standard Django Application developed with python3.7. Use `pip install -U -r requirements.txt` in a seperate python environment to install the dependencies. Make sure to adjust the `ALLOWED_HOSTS`, `DEBUG`, `SECRET_KEY`, `MEDIA_ROOT` and `DATABASES` settings in a `local_settings.py` for use in production. See the [Django Docs](https://docs.djangoproject.com/en/2.2/ref/settings/) on what these do.

Run `python3 manage.py migrate` to initialize the database.

Run `python3 manage.py collectstatic` to collect all static files into the `static.dist` folder, from where all files under `/static/` should be served from. Also, everything under `/media/` should point to the `MEDIA_ROOT` you configured. You probably want to use a webserver and uwsgi or something similar for the setup.

All configuration/management views are only visible to logged in superusers. Using `./manage.py createsuperuser`, create a new superuser and login on the webpage.

