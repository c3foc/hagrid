
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

We use uv for package management. Install uv and run `uv sync` to install the dependencies.

#### Development

Setting up hagrid for local development is simple.

1. Copy `.env.example` to `.env` and adjust the settings as needed. The defaults should work for development.
2. Run `./manage.py migrate` to setup a test database.
3. Run `./manage.py devdata` to setup a default admin user (admin/admin) and some initial data).
4. Run `./manage.py runserver` to start the local development server.

#### Production

Make sure to adjust the following settings in a `.env` file for use in production.

* `ALLOWED_HOSTS`
* `DEBUG` (should be `False`)
* `SECRET_KEY` (should be random and secret)
* `SITE_URL` (URL for building absolute links)
* `DATA_DIR` (where to store data like logs or user-uploaded content)
* `DATABASE_URL` for which DB to use.
* `DEFAULT_FROM_EMAIL` for sending emails (e.g. for password resets).

See the [Django Docs](https://docs.djangoproject.com/en/2.2/ref/settings/) or the comments in `settings.py` on what these do.

hagrid requires an ASGI server like daphne to run, as well as redis for caching and event streaming. You can use something like nginx to serve static and media files directly and proxy requests to the ASGI server.

Nginx must be configured for EventStream under the `/api/events/` route: 

```
location /api/event/ {
    proxy_pass # ......
    
    # Crucial for Server-Sent Events
    proxy_set_header Connection "";
    # Disable buffering to allow real-time streaming
    proxy_buffering off;
    proxy_cache off;
    # Increase timeouts for long-lived connections
    proxy_read_timeout 24h;
    proxy_send_timeout 24h;
}
```

Run `python3 manage.py migrate` to initialize the database.

Run `python3 manage.py collectstatic` to collect all static files into the `static.dist` folder, from where all files under `/static/` should be served from. Also, everything under `/media/` should point to the `MEDIA_ROOT` you configured. You probably want to use a webserver and uwsgi or something similar for the setup.

All configuration/management views are only visible to logged in superusers. Using `./manage.py createsuperuser`, create a new superuser and login on the webpage.


### License

There is no statement yet on the license of this software, but please be aware that
the fonts distributed alongside this software (in `hagrid/static/fonts`) are
shipping with their own respective licenses.
