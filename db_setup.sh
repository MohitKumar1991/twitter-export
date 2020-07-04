#!/usr/bin/env bash
source $HOME/.poetry/env
echo `which poetry`
poetry run recreate_db
