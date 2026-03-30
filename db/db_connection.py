import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mysql.connector
from config.get_config import get_config
from utils.nagios_data_query import nagios_sql_query

def get_sql_data():
    credentials = get_config()

    cnx = mysql.connector.connect(
        host=credentials["DB_HOST"],
        user=credentials["DB_USER"],
        password=credentials["DB_PASSWORD"],
        database=credentials["DB_NAME"] 
    )

    cur = cnx.cursor()

    try:
        # print("Executing query:", nagios_sql_query)
        cur.execute(nagios_sql_query)
        rows = cur.fetchall()
        columns = [data[0] for data in cur.description]
        return {
            "rows":rows,
            "columns":columns
        }
    except Exception as e:
        print("Error executing query:", e)
    finally:
        cur.close()


if __name__ == "__main__":
    print(get_sql_data())