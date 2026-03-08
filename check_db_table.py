import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to database
conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT')
)

cursor = conn.cursor()

# Check the api_app_stocknews table structure
print('=== Checking api_app_stocknews table structure ===')
cursor.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'api_app_stocknews'
    ORDER BY ordinal_position;
""")

columns = cursor.fetchall()
for col in columns:
    print(f'{col[0]:20} | {col[1]:20} | Nullable: {col[2]:5} | Default: {col[3]}')

print('\n=== Checking constraints on api_app_stocknews ===')
cursor.execute("""
    SELECT constraint_name, constraint_type
    FROM information_schema.table_constraints
    WHERE table_name = 'api_app_stocknews';
""")

constraints = cursor.fetchall()
for constraint in constraints:
    print(f'{constraint[0]:40} | Type: {constraint[1]}')

print('\n=== Checking primary key details ===')
cursor.execute("""
    SELECT kcu.column_name, kcu.ordinal_position
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
    WHERE tc.table_name = 'api_app_stocknews'
        AND tc.constraint_type = 'PRIMARY KEY';
""")

pk_columns = cursor.fetchall()
for pk in pk_columns:
    print(f'Primary Key Column: {pk[0]} (Position: {pk[1]})')

cursor.close()
conn.close()
