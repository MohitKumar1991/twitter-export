mac_setup:
	./mac_setup

create_db:
	poetry run python -m tw_sub.recreate_db

start_server:
	poetry run gunicorn tw_sub.main:app

start_worker:
	poetry run python -m tw_sub.worker start

stop_worker:
	poetry run python -m tw_sub.worker stop