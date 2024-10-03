import mysql.connector

def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='256481@dinal',
            database='flight_game',
            autocommit=True
        )
        if connection.is_connected():
         return connection
    except mysql.connector.Error as err:
        print(f'error: {err}')
        return None
def close_connection(connection):
    if connection.is_connected():
        connection.close()
