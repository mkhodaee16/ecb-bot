import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def init_database():
    # Connect to MySQL server
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST'),
        port=int(os.getenv('MYSQL_PORT')),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD')
    )
    
    cursor = conn.cursor()
    
    # Read and execute schema.sql
    with open('schema.sql', 'r') as f:
        sql_commands = f.read()
        
    for command in sql_commands.split(';'):
        if command.strip():
            cursor.execute(command)
            
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == '__main__':
    init_database()