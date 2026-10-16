#!/usr/bin/python3

"""
Establish a connection to the local postgreSQL database aimed to update the table under the DB named "hw_and_sw".
"""

import psycopg2
import json
import sys
import os

jsondata = str(input("Which file you want to import to the database: "))
#tname = str(input("which table you want to update: "))

db_user = "postgres"
db_pwd = "postgres"
db_port = "5432"
db_host = "127.0.0.1"
db_name = "hw_and_sw"

print(jsondata)
print(type(jsondata))

with open(jsondata,'r') as file:
    jdata = json.load(file)

    print(jdata)

try:
    conn = psycopg2.connect(
        dbname = db_name,
        user = db_user,
        password = db_pwd,
        host = db_host,
        port = db_port
        )
    print("DB connection openned successfully")

    conn.autocommit = True
    cur = conn.cursor()

    #cur.execute("select version();")

    #jsondata = json.loads(json_string)

    for entry in jdata:
        release_version = entry['version'].split('.')[0] + '.0'
        query = '''
        INSERT INTO code_level (release, version, nick_name)
        VALUES (%s, %s, %s)
        ON CONFLICT (version) DO UPDATE SET
        nick_name = EXCLUDED.nick_name;
        '''
        cur.execute(query,(release_version,entry['version'],entry['nick name']))

    #data = cur.fetchone()
    #print("Database version:",data)

    cur.close()
    conn.close()

except psycopg2.Error as e:
    print("Unable to connect to the database")
    print(e)
