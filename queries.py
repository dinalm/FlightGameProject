import mysql.connector

# Function for getting clues
def get_clues_by_airport(connection, airport_id):
    try:
        cursor = connection.cursor()
        sql_query = "SELECT description, validity FROM clues WHERE airport_id = %s"
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

# Retrieve player's current fuel
def get_player_fuel(connection, player_id):
    try:
        cursor = connection.cursor()
        sql_query = "SELECT fuel_units FROM player WHERE player_id = %s"
        cursor.execute(sql_query, (player_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            print(f'Player with ID {player_id} not found')
            return None

    except mysql.connector.Error as err:
        print(f'error: {err}')
        return None

# Update player's fuel after traveling or refueling
def update_player_fuel(connection, player_id, fuel_amount):
    try:
        cursor = connection.cursor()
        sql_query = "UPDATE player SET fuel_units = %s WHERE player_id = %s"
        cursor.execute(sql_query, (fuel_amount, player_id))
        connection.commit()
        print(f"Player's fuel updated to {fuel_amount:.2f} units.")

    except mysql.connector.Error as err:
        print(f'error: {err}')

# Checking for fuel price and the airport name
def get_fuel_info_at_airport(connection, airport_id):
    try:
        cursor = connection.cursor()
        sql_query = "SELECT name, fuel_price FROM airport WHERE id = %s"
        cursor.execute(sql_query, (airport_id,))
        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        else:
            return None, None

    except mysql.connector.Error as err:
        print(f'error: {err}')
        return None

from geopy.distance import geodesic

def calculate_fuel_requirement(current_airport_id, destination_airport_id, connection):
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT latitude_deg, longitude_deg FROM airport WHERE id = %s", (current_airport_id,))
        current_airport = cursor.fetchone()

        cursor.execute("SELECT latitude_deg, longitude_deg FROM airport WHERE id = %s", (destination_airport_id,))
        destination_airport = cursor.fetchone()

        if current_airport and destination_airport:
            # Calculate the distance using geodesic
            distance = geodesic((current_airport[0], current_airport[1]), (destination_airport[0], destination_airport[1])).kilometers
            fuel_consumption_rate_per_km = 0.5
            return distance * fuel_consumption_rate_per_km
        else:
            return 0  # Return 0 if one of the airport details is not found
    except Exception as e:
        print(f"Error calculating fuel requirement: {e}")
        return 0  # Return 0 in case of any exception

def get_airport_name(connection, airport_id):
    try:
        cursor = connection.cursor()
        sql_query = "SELECT name FROM airport WHERE id = %s"
        cursor.execute(sql_query, (airport_id,))
        result = cursor.fetchone()
        return result[0] if result else "Unknown Airport"
    except Exception as e:
        print(f"Error getting airport name: {e}")
        return "Unknown Airport"

def fetch_airport_and_country(connection, airport_id):
    cursor = connection.cursor()
    sql_query = "SELECT airport.name, country.name FROM airport JOIN country ON airport.iso_country = country.iso_country WHERE airport.id = %s"
    cursor.execute(sql_query, (airport_id,))
    result = cursor.fetchone()
    if result:
        return result[0], result[1]  # airport name, country name
    else:
        return None, None  # No data found for this airport ID


def fetch_airport_coordinates(connection, airport_id):
    cursor = connection.cursor()
    sql_query = "SELECT latitude_deg, longitude_deg FROM airport WHERE id = %s"
    cursor.execute(sql_query, (airport_id,))
    result = cursor.fetchone()
    if result:
        return result[0], result[1]  # latitude, longitude
    else:
        return None, None  # No data found


def update_player_location(connection, player_id, new_location_id):
    try:
        cursor = connection.cursor()

        # Fetch latitude and longitude for the new airport
        sql_query = "SELECT latitude_deg, longitude_deg FROM airport WHERE id = %s"
        cursor.execute(sql_query, (new_location_id,))
        result = cursor.fetchone()
        if result:
            new_latitude, new_longitude = result

            # Update the player's location and coordinates
            update_query = "UPDATE player SET current_airport_id = %s, current_latitude = %s, current_longitude = %s WHERE player_id = %s"
            cursor.execute(update_query, (new_location_id, new_latitude, new_longitude, player_id))
            connection.commit()
            print("Player location and coordinates updated successfully.")
        else:
            print("No such airport found.")
    except Exception as e:
        print(f"Error updating player location and coordinates: {e}")


def list_all_airports_except_current(connection, current_airport_id):
    try:
        # Fetch all airports excluding the current one
        cursor = connection.cursor()
        sql_query = "SELECT airport.name, country.name, country.iso_country FROM airport JOIN country ON airport.iso_country = country.iso_country WHERE airport.id != %s ORDER BY country.name, airport.name"
        cursor.execute(sql_query, (current_airport_id,))  # Pass current airport id to the query
        airports = cursor.fetchall()

        if not airports:
            print("No other airports available.")
            return []

        return airports  # Just return the list of airports

    except Exception as e:
        print(f"Error fetching airports: {e}")
        return []

def start_new_game(connection, player_id):
    try:
        cursor = connection.cursor()
        # Insert a new row into game_state for the new game
        insert_query = "INSERT INTO game_state (player_id, criminal_caught, moves_count) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (player_id, False, 0))  # Initial values: criminal_caught = False, moves_count = 0
        connection.commit()

        # Get the newly created game_id
        cursor.execute("SELECT LAST_INSERT_ID()")
        game_id = cursor.fetchone()[0]
        print(f"New game started with game_id: {game_id}")

        return game_id
    except mysql.connector.Error as err:
        print(f"Error starting new game: {err}")
        return None

def update_game_state_after_move(connection, game_id, criminal_caught):
    try:
        cursor = connection.cursor()

        # Get the current number of moves
        cursor.execute("SELECT moves_count FROM game_state WHERE game_id = %s", (game_id,))
        current_moves = cursor.fetchone()[0]

        # Increment the move count
        new_moves_count = current_moves + 1

        # Update the game_state with the new move count and if the criminal is caught
        update_query = "UPDATE game_state SET moves_count = %s, criminal_caught = %s WHERE game_id = %s"
        cursor.execute(update_query, (new_moves_count, criminal_caught, game_id))
        connection.commit()
        print(f"Game state updated: {new_moves_count} moves, criminal caught: {criminal_caught}")
    except mysql.connector.Error as err:
        print(f"Error updating game state: {err}")

def check_if_criminal_caught(connection, game_id):
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT criminal_caught FROM game_state WHERE game_id = %s", (game_id,))
        result = cursor.fetchone()
        return result[0] if result else False
    except mysql.connector.Error as err:
        print(f"Error checking game status: {err}")
        return False

def get_or_create_player(connection):
    while True:
        # Ask the player for their screen name or if they want to create a new profile
        player_name = input("Please enter your screen name or type 'new' to create a new profile: ")

        if player_name.lower() == 'new':
            # If the player types 'new', start the registration process
            player_id = create_new_player(connection)
            if player_id:  # If registration was successful, return the new player ID
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
            default_airport_id = 1  # Assuming '1' is the default airport ID for new players
            starting_fuel = 250  # Set starting fuel units to 250

            # Fetch the name of the default starting airport
            cursor.execute("SELECT name FROM airport WHERE id = %s", (default_airport_id,))
            default_airport_name = cursor.fetchone()[0]  # Fetch the airport name

            # Insert the new player with the default current_airport_id and starting fuel_units
            query = "INSERT INTO player (screen_name, current_airport_id, fuel_units) VALUES (%s, %s, %s)"
            cursor.execute(query, (screen_name, default_airport_id, starting_fuel))
            connection.commit()

            # Fetch the new player ID
            player_id = cursor.lastrowid
            print(f"Welcome, {screen_name}! Your new player ID is {player_id}.")
            print(f"You start at {default_airport_name} airport with {starting_fuel} fuel units.")

            return player_id


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



