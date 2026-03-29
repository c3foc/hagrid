
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

For now, this is a pretty standard Django Application developed with python3.7. Use `pip install -U -r requirements.txt` (in a seperate python environment/virtualenv) to install the dependencies.

#### Development

Setting up hagrid for local development is simple.

1. Run `./manage.py migrate` to setup a test database.
2. Run `./manage.py createsuperuser` to setup a default admin user.
3. Run `./manage.py runserver` to start the local development server.


#### Development with Docker

To use the `docker` setup for hagrid you need `docker` or `podman` and
`docker-compose` or `podman-compose` installed on your machine.

1. Run `docker-compose up` to start the local development server.
2. Run `docker-compose exec web python ./manage.py migrate` to setup a test database.
3. Run `docker-compose exec web python ./manage.py createsuperuser` to setup a default admin user.

The first time `docker-compose up` is run it will build a docker image with all
dependencies installed. If you change the dependencies you need to rebuild the image
with `docker-compose build`.

#### Production

Make sure to adjust the following settings in a `local_settings.py` for use in production.

* `ALLOWED_HOSTS`
* `DEBUG` (should be `False`)
* `SECRET_KEY` (should be random and secret)
* `SITE_URL` (URL for building absolute links)
* `MEDIA_ROOT` (where to put user-uploaded content)
* `DATABASES`

See the [Django Docs](https://docs.djangoproject.com/en/2.2/ref/settings/) or the comments in `settings.py` on what these do.

Run `python3 manage.py migrate` to initialize the database.

Run `python3 manage.py collectstatic` to collect all static files into the `static.dist` folder, from where all files under `/static/` should be served from. Also, everything under `/media/` should point to the `MEDIA_ROOT` you configured. You probably want to use a webserver and uwsgi or something similar for the setup.

All configuration/management views are only visible to logged in superusers. Using `./manage.py createsuperuser`, create a new superuser and login on the webpage.


### License

There is no statement yet on the license of this software, but please be aware that
the fonts distributed alongside this software (in `hagrid/static/fonts`) are
shipping with their own respective licenses.
