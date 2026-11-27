import os

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url


load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE") or os.getenv("MYSQL_DB", "netpulse")
MYSQL_USER = os.getenv("MYSQL_USER", "netpulse")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

DATABASE_URL = (
    make_url(os.environ["DATABASE_URL"])
    if os.getenv("DATABASE_URL")
    else URL.create(
        drivername="mysql+pymysql",
        username=MYSQL_USER,
        password=MYSQL_PASSWORD,
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        database=MYSQL_DATABASE,
    )
)