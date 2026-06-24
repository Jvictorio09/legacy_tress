web: python manage.py collectstatic --noinput && python manage.py migrate --noinput && gunicorn MyProject.wsgi --bind 0.0.0.0:$PORT
