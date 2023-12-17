import csv
import psycopg2

# Database connection details
db_host = ''
db_name = ''
db_user = ''
db_password = ''

# CSV file path
csv_file = 'example.csv'

# Specific group ID to clean the table
specific_group_id = ''

# Function to clean the table based on specific_group_id
def clean_table():
    sql = 'select "user".name from "user" join "group_user" on "group_user".user_id = "user".id join "group" on "group".id = "group_user".group_id where "group".id = 1';
    conn = psycopg2.connect(host=db_host, dbname=db_name, user=db_user, password=db_password)
    cur = conn.cursor()
    cur.execute('DELETE FROM contest_winner WHERE user_id IN (select "user".id from "user" join "group_user" on "group_user".user_id = "user".id join "group" on "group".id = "group_user".group_id where "group".id = %s)', (specific_group_id,))
    conn.commit()
    cur.close()
    conn.close()

# Function to insert data from CSV into contest_winner table
def insert_data():
    cid = -1000
    conn = psycopg2.connect(host=db_host, dbname=db_name, user=db_user, password=db_password)
    cur = conn.cursor()
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            tg_username = row['tg_username']
            wins = row['wins']
            cur.execute('SELECT COUNT(*) FROM contest_winner WHERE user_id = (SELECT "user".id FROM "user" WHERE name  = %s)', (tg_username,))
            current_count = cur.fetchone()[0]

            difference = int(wins) - int(current_count)
            print(1)
            print(tg_username, wins)
            print(wins, current_count)
            if difference > 0:
                for _ in range(difference):
                    print(1)
                    cur.execute("INSERT INTO contest (id, contest_name, contest_duration_sec, created_date, group_id) VALUES (%s, 'migration', -1, now(), 1)", (cid,))
                    conn.commit()
                    cur.execute('INSERT INTO contest_winner (user_id, contest_id) VALUES ((SELECT id FROM "user" WHERE name  = %s), %s)', (tg_username, cid))
                    cid -= 1
    conn.commit()
    cur.close()
    conn.close()

# Clean the table first

# Insert data from CSV into the table
insert_data()

