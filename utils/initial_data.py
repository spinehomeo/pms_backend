import logging

from sqlmodel import Session

from core.db import engine, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init() -> None:
    with Session(engine) as session:
        init_db(session)


def main() -> None:
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")


if __name__ == "__main__":
    main()


# (pms-backend) F:\2_PROJECTS\B_PMS\pms_backend>python.exe -m utils.initial_data
# INFO:__main__:Creating initial data
# INFO:__main__:Initial data created
