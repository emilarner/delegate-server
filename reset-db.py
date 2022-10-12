import psycopg2
import blessed
import sys
import config

t = blessed.Terminal()

def main():
    print(t.red_bold("Warning! This will delete all Delegate Server data and start anew!!!"))

    # Verify if they want to continue
    if (input("Do you wish to continue (Y/y/N/n)?: ") not in ["y", "Y"]):
        print("Exiting with code -1...")
        sys.exit(-1)

    database = psycopg2.connect(
        host = config.Database.Host,
        dbname = config.Database.Name, 
        user = config.Database.Username, 
        password = config.Database.Password
    )

    cursor = database.cursor()

    cursor.execute("DROP TABLE IF EXISTS Users;")
    cursor.execute("DROP TABLE IF EXISTS Channels;")
    #cursor.execute("DROP TABLE IF EXISTS ChannelQueryables;")
    #cursor.execute("DROP TABLE IF EXISTS ChannelMessages;")
    #cursor.execute("DROP TABLE IF EXISTS UserMessages;")
    #cursor.execute("DROP TABLE IF EXISTS ")

    database.commit()


if (__name__ == "__main__"):
    main()