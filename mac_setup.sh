#!/bin/bash
# setup.sh 
# Setup script for Flask Boilerplate only for Mac machines. Look at docs for windows

set -o errexit  # exit on any errors

brew install python3
brew upgrade python3
brew install postgresql
brew link postgresql
brew services start postgresql
echo "-----> Install Poetry"
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python | indent

source $HOME/.poetry/env

# wait until postgres is started
while ! pg_isready -h "localhost" -p "5432" > /dev/null 2> /dev/null; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 3
done

>&2 echo "Postgres is up - executing command"

createdb || true    # create init database - pass on error 
psql -c "create user testusr with password 'password';" || true     # pass on error
psql -c "ALTER USER testusr WITH SUPERUSER;" || true
# psql -c "create database testdb owner testusr encoding 'utf-8';"
# psql -c "GRANT ALL PRIVILEGES ON DATABASE testdb TO testusr;"

make create_db