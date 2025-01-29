import os # allows access to host computer's environment variables and OS-level functionality (ex. os.mkdir())
import psycopg2 # PostgreSQL adapter, allows python applications to interact with Postgresql databases
from psycopg2.extras import RealDictCursor # helps return database results as dictionaries
from contextlib import contextmanager # aids in safe database connections

class Database:
    # dunder (double underline) method, allow for customizability of Python's built-in operations (ex. object construction, addition, subtraction)
    def __init__(self):

        # database connection settings so that the app knows where and how to connect to the database
        self.config = {
            'host': os.getenv('POSTGRES_HOST', 'db'), # possible places the database could be hosted is locally, in a container, or in the cloud
            'database': os.getenv('POSTGRES_DB', 'nba_stats'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD') # 2nd parameter is default value, there's no default password for security purposes
        }
    

    # this method helps us safely manage database connections
    @contextmanager # decorator that turns a function into a context manager, which allows the function to be used with Python's "with" statement
    def get_cursor(self): 
        connection = psycopg2.connect(**self.config, cursor_factory=RealDictCursor)
        try:
            yield connection.cursor()
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally: # always runs
            connection.close()

    def init_db(self):
        # with statement ensures automatic resource cleanup even if an error occurs
        # a cursor is an object that allows you to interact with a database by executing SQL queries and fetchign results
        with self.get_cursor() as cur: 
            cur.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id VARCHAR(10) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    team VARCHAR(50),
                    position VARCHAR(10),
                    height VARCHAR(10),
                    weight INTEGER                        
                );
                CREATE TABLE IF NOT EXISTS player_stats (
                    id SERIAL PRIMARY KEY,
                    player_id VARCHAR(10) REFERENCES players(id),
                    season VARCHAR(10),
                    games_played INTEGER,
                    points DECIMAL,
                    rebounds DECIMAL,
                    assists DECIMAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

db = Database()

