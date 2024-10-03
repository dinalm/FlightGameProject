import mysql.connector

# Function for getting clues
def get_clues_by_airport(connection, airport_id):
    try:
        cursor = connection.cursor()
        sql_query = "SELECT description FROM clues WHERE airport_id = %s"
        cursor.execute(sql_query, (airport_id,))
        return cursor.fetchall()

    except mysql.connector.Error as err:
        print(f'error: {err}')
        return None

# Function for getting npcs
def get_npcs_by_airport(connection, airport_id):
    try:
        cursor = connection.cursor()
        sql_query = "SELECT name, role, information FROM npc WHERE airport_id = %s"
        cursor.execute(sql_query, (airport_id,))
        return cursor.fetchall()

    except mysql.connector.Error as err:
        print(f'error: {err}')
        return None

# Function for updating player location
def update_player_location(connection, player_id, new_airport_id):
    cursor = connection.cursor()
    cursor.execute("SELECT latitude_deg, longitude_deg FROM airport WHERE id = %s", (new_airport_id,))
    result = cursor.fetchone()

    if result:
        new_latitude, new_longitude = result

        # Update player's current location (airport ID and coordinates)
        update_query = "UPDATE player SET current_airport_id = %s, current_latitude = %s, current_longitude = %s WHERE player_id = %s"
        cursor.execute(update_query, (new_airport_id, new_latitude, new_longitude, player_id))
        connection.commit()
        return True

    else:
        print("No such airport found. Unable to update player location.")
        return False

# Function for listing all the remaining airports
def list_all_airports_except_current(connection, current_airport_id):
    try:
        cursor = connection.cursor()
        sql_query = "SELECT airport.id, airport.name, country.name FROM airport JOIN country ON airport.iso_country = country.iso_country WHERE airport.id != %s ORDER BY country.name, airport.name"
        cursor.execute(sql_query, (current_airport_id,))
        airports = cursor.fetchall()
        return airports
    except Exception as e:
        print(f"Error fetching airports: {e}")
        return []

# Function insert data into game_state table when start a new game
def start_new_game(connection, player_id):
    try:
        cursor = connection.cursor()
        insert_query = "INSERT INTO game_state (player_id, criminal_caught, moves_count) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (player_id, False, 0))
        connection.commit()

        # Get the newly created game_id
        cursor.execute("SELECT LAST_INSERT_ID()")
        game_id = cursor.fetchone()[0]
        return game_id

    except mysql.connector.Error as err:
        print(f"Error starting new game: {err}")
        return None

# Function for updating game_state table data
def update_game_state(connection, game_id, player_id, moves_count=None, criminal_caught=None, game_over=None):
    cursor = connection.cursor()

    update_fields = []
    update_values = []

    # If the moves count is passed, update it in the game_state table
    if moves_count is not None:
        update_fields.append("moves_count = %s")
        update_values.append(moves_count)

    # If the criminal_caught status is passed, update it in the game_state table
    if criminal_caught is not None:
        update_fields.append("criminal_caught = %s")
        update_values.append(criminal_caught)

    # If the game_over status is passed, update it in both game_state and player tables
    if game_over is not None:
        update_fields.append("game_over = %s")
        update_values.append(game_over)

    # Updating the game_state table fields data
    if update_fields:
        sql_update = f"UPDATE game_state SET {', '.join(update_fields)} WHERE game_id = %s"
        update_values.append(game_id)  # Add game_id to the values
        try:
            cursor.execute(sql_update, tuple(update_values))
            connection.commit()
        except Exception as e:
            print(f"Error updating game state: {e}")

    # Updating the player table's game_over field
    if game_over is not None:
        try:
            cursor.execute("UPDATE player SET game_over = %s WHERE player_id = %s", (game_over, player_id))
            connection.commit()
        except Exception as e:
            print(f"Error updating player's game_over status: {e}")

        # If the game is marked as over (game_over = True or game_over = 1), delete the player's travel history
        if game_over:
            try:
                cursor.execute("DELETE FROM player_movement WHERE player_id = %s", (player_id,))
                connection.commit()
            except Exception as e:
                print(f"Error deleting player's travel history: {e}")


#------------------------ Functions for retrieving and registering players------------------------------#

def retrieve_or_register_player(connection, screen_name):
    cursor = connection.cursor()
    cursor.execute("SELECT player_id FROM player WHERE screen_name = %s", (screen_name,))
    result = cursor.fetchone()
    if result:
        print(f"Welcome back, {screen_name}!")
        return result[0]
    else:
        print(f"No profile found for {screen_name}. Creating a new profile...")
        return create_new_player(connection)


def get_or_create_player(connection):
    while True:
        # Ask the player for their screen name or if they want to create a new profile
        player_name = input("Please enter your screen name or type 'new' to create a new profile: ")
        if player_name.lower() == 'new':
            player_id = create_new_player(connection)
            if player_id:
                return player_id
            else:
                print("Registration canceled or failed. Returning to the main menu...")
        else:
            # Try to find the player with the provided screen name
            player_id = retrieve_or_register_player(connection, player_name)
            if player_id:
                return player_id
            else:
                print(f"No player found with the screen name '{player_name}'.")
                print("Please try again or type 'new' to create a new profile.")


def create_new_player(connection):
    cursor = connection.cursor()

    while True:
        # Prompt the player for their desired screen name
        screen_name = input("Enter your desired screen name to create a new player profile (or type 'back' to go back): ")

        # Allow the player to go back to the previous menu if they made a mistake
        if screen_name.lower() == 'back':
            print("Returning to the previous menu...")
            return None

        # Check if the screen name already exists
        cursor.execute("SELECT player_id FROM player WHERE screen_name = %s", (screen_name,))
        existing_player = cursor.fetchone()

        if existing_player:
            # If a player with the same screen name already exists, prevent registration
            print(f"Error: The screen name '{screen_name}' is already taken. Please choose a different name.")
        else:
            # Set the default airport ID and starting fuel
            default_airport_id = 1
            starting_fuel = 250

            # Fetch the name of the default starting airport
            cursor.execute("SELECT name FROM airport WHERE id = %s", (default_airport_id,))
            default_airport_name = cursor.fetchone()[0]  # Fetch the airport name

            # Insert the new player with the default current_airport_id and starting fuel_units
            query = "INSERT INTO player (screen_name, current_airport_id, fuel_units) VALUES (%s, %s, %s)"
            cursor.execute(query, (screen_name, default_airport_id, starting_fuel))
            connection.commit()

            # Fetch the new player ID
            player_id = cursor.lastrowid
            print(f"Welcome, {screen_name}!")
            print(f"You start at {default_airport_name} with {starting_fuel} fuel units.")

            return player_id
#-----------------------------------------------------End------------------------------------------------------------#

# Function for displaying player status table
from prettytable import PrettyTable
def show_player_status(connection, player_id):
    cursor = connection.cursor()

    # Fetch player's current status
    cursor.execute(
        "SELECT screen_name, fuel_units, refuel_attempts, current_airport_id "
        "FROM player WHERE player_id = %s", (player_id,)
    )
    player_data = cursor.fetchone()

    if player_data:
        screen_name = player_data[0]
        fuel_units = player_data[1]
        refuel_attempts = player_data[2]
        current_airport_id = player_data[3]

        # Fetch current airport name
        cursor.execute("SELECT airport.name, country.name FROM airport JOIN country ON airport.iso_country = country.iso_country WHERE airport.id = %s", (current_airport_id,))
        current_airport = cursor.fetchone()

        print("\n!----------Player Status----------!")
        print(f"Screen Name: {screen_name}")
        print(f"Current Location: {current_airport[0]} ({current_airport[1]})")
        print(f"Fuel Units: {fuel_units}")
        print(f"Remaining Refuel Attempts: {refuel_attempts}/5")
        print("!---------------------------------!")

        # Fetch the player's movement history
        cursor.execute(
            "SELECT a1.name, a2.name, player_movement.distance_traveled, player_movement.movement_date "
            "FROM player_movement "
            "JOIN airport a1 ON player_movement.departure_airport_id = a1.id "
            "JOIN airport a2 ON player_movement.destination_airport_id = a2.id "
            "WHERE player_movement.player_id = %s "
            "ORDER BY player_movement.movement_date", (player_id,)
        )
        movements = cursor.fetchall()

        if movements:
            print("\n!----------Travel History---------!")
            table = PrettyTable()
            table.field_names = ["Departure Airport", "Destination Airport", "Distance (Km)", "Date & Time"]

            # Add rows to the table
            for movement in movements:
                departure_airport = movement[0]
                destination_airport = movement[1]
                distance_traveled = movement[2]
                movement_date = movement[3]
                table.add_row([departure_airport, destination_airport, f"{distance_traveled:.2f}", movement_date])

            print(table)
        else:
            print("No travel history available.")
    else:
        print("Player not found.")



