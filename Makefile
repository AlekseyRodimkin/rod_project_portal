activate:
	source $(poetry env info --path)/bin/activate

migrate:
	python rod_project_portal/manage.py migrate

mk_migrate:
	python rod_project_portal/manage.py makemigrations

admin:
	python rod_project_portal/manage.py createsuperuser

run:
	python rod_project_portal/manage.py runserver

build:
	docker build -t rod_project_portal --no-cache .

start:
	docker run -d -p 8000:8000 --name rp_portal rod_project_portal

static:
	 rm -rf rod_project_portal/static && python rod_project_portal/manage.py collectstatic

dev_start:
	poetry run python -m uvicorn rod_project_portal.asgi:application --host 0.0.0.0 --port 8443 --ssl-keyfile key.pem --ssl-certfile cert.pem --app-dir rod_project_portal

black:
	poetry run black .