import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def init_database():
    try:
        # Connect to MySQL server
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            port=int(os.getenv('MYSQL_PORT')),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD')
        )
        
        cursor = conn.cursor()
        
        # Check if the database already exists
        database_name = os.getenv('MYSQL_DATABASE')
        cursor.execute(f"SHOW DATABASES LIKE '{database_name}'")
        result = cursor.fetchone()
        
        if result:
            print(f"Database '{database_name}' already exists.")
            cursor.close()
            conn.close()
            return
        
        # Create the database if it doesn't exist
        cursor.execute(f"CREATE DATABASE {database_name}")
        print(f"Database '{database_name}' created successfully.")
        
        # Switch to the new database
        cursor.execute(f"USE {database_name}")
        
        # Read and execute schema.sql
        schema_file_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        if not os.path.exists(schema_file_path):
            raise FileNotFoundError(f"Schema file '{schema_file_path}' not found.")
        
        with open(schema_file_path, 'r') as f:
            sql_commands = f.read()
        
        for command in sql_commands.split(';'):
            if command.strip():
                cursor.execute(command)
        
        conn.commit()
        print("Schema executed successfully.")
        
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    except FileNotFoundError as err:
        print(err)
    except Exception as err:
        print(f"Unexpected error: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    init_database()