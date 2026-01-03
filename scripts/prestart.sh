#! /usr/bin/env bash

#!/usr/bin/env bash

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Run migrations
alembic upgrade head

# Create initial data in DB
python app/initial_data.py

# (pms-backend) F:\2_PROJECTS\B_PMS\pms_backend>python.exe -m utils.initial_data
# INFO:__main__:Creating initial data
# INFO:__main__:Initial data created
