mac_setup:
	./mac_setup

setup: start_dev_db
	pip3 install virtualenv
	virtualenv venv
	venv/bin/pip install -r requirements.txt -r requirements-dev.txt
	venv/bin/python manage.py recreate_db

run_server:
	venv/bin/python manage.py runserver

heroku_setup:
	./db_setup.sh