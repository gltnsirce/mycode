#!/usr/bin/python3

import psycopg2
import json
import os
import sys

# Database connection info
db_user = "postgres"
db_pwd = "postgres"
db_port = "5432"
db_host = "127.0.0.1"
db_name = "hw_and_sw"

# Establish the connection to the database.
def establish_DB_connection():
    try:
        conn = psycopg2.connect(
            dbname = db_name,
            user = db_user,
            password = db_pwd,
            host = db_host,
            port = db_port
            )
        print("DB connection openned successfully")
        return conn
    except psycopg2.Error as e:
        print("Unable to eastablish the connection to the PostgreSQL database.")
        print(e)
        return None
    
# Manually update the database.
# The table named "code_level" is save all the code level and nick name of VxRail release versions.
def update_code_level_manual(conn):
    if conn is not None:
        try:
            print("This function is used to update the table named \"code_level\" under the \"hw_and_sw\".")
            cur = conn.cursor()
            cont_ops = "y"
            ops_status = "y"
            while cont_ops == ops_status:
                release = input("Enter the release train verison:")
                version = input("Enter the code level:")
                nick_name = input("Enter the nick name of VxRail code level:")
                cur.execute("INSERT INTO code_level (release, code_level, code_name) VALUES (%s, %s, %s) "
                    "ON CONFLICT (code_level) DO UPDATE SET code_name = EXCLUDED.code_name;",
                    (release, version, nick_name))
                cont_ops = input("Begin to update the Table, type \"y\" to coninue to update the database or type any other character to stop update database.")
                conn.commit()
                print("The database updated completed.")
        except psycopg2.Error as e:
            print("Error updating the database:",e)
        finally:
            cur.close()
            conn.close()
    else:
        print("No connection to the PostgreSQL.")

# Update the database via import the json file with the correct key value.
def update_database_json(conn,json_file_path):
    if conn is not None:
        try:
            cur = conn.cursor()
            with open(json_file_path, 'r') as file:
                entries = json.load(file)
            for entry in entries:
                cur.execute(
                    "INSERT INTO code_level (release, code_level, code_name) VALUES (%s, %s, %s) "
                    "ON CONFLICT (code_level) DO UPDATE SET code_name = EXCLUDED.code_name;",
                    (entry['release'], entry['version'], entry['nick name'])
                )
            conn.commit()
            print("The database updated completed.")
        except (psycopg2.Error,FileNotFoundError,json.JSONDecodeError) as e:
            print("Error updating the database:", e)
        finally:
            cur.close()
            conn.close()
    else:
        print("No connection to the database.")

# main function
if __name__ == "__main__":
    conn = establish_DB_connection()
    if conn:
        choice = input("Update via (1) manual input or (2) JSON file, enter the 1 or 2:")
        if choice == "1":
            update_code_level_manual(conn)
        elif choice == "2":
            json_file_path = input("Enter the path of the JSON file:")
            update_database_json(conn, json_file_path)
        else:
            print("Invalid input to choice the options of update the database.")
