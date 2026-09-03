#!/usr/bin/env bash
set -euo pipefail

psql "$1" -v ON_ERROR_STOP=1 -c "CREATE ROLE app WITH LOGIN CREATEDB PASSWORD '${PATRONI_APP_PASSWORD}';"
psql "$1" -v ON_ERROR_STOP=1 -c "CREATE DATABASE citylab OWNER app;"
