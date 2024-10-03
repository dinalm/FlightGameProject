from queries import (get_clues_by_airport, get_npcs_by_airport, list_all_airports_except_current, update_player_location, update_game_state)

# Game logic for player refueling
def refuel_player(connection, player_id, fuel_to_add):
    cursor = connection.cursor()
    try:
        # Fetch player's current fuel level and refuel attempts
        cursor.execute("SELECT fuel_units, refuel_attempts FROM player WHERE player_id = %s", (player_id,))
        result = cursor.fetchone()

        if result:
            current_fuel = result[0]
            refuel_attempts = result[1]

            # Check if the player has already used all refuel attempts
            if refuel_attempts >= 5:
                print("You have used all 5 refuel attempts and cannot refuel anymore.")
                return False

            # Check if the fuel to add exceeds the allowed limit per session
            if fuel_to_add > 1000:
                print("You cannot refuel more than 1000 units in a single session.")
                return False

            # Calculate the new fuel amount and increment refuel attempts
            new_fuel_amount = current_fuel + fuel_to_add
            refuel_attempts += 1
            cursor.execute("UPDATE player SET fuel_units = %s, refuel_attempts = %s WHERE player_id = %s",
                           (new_fuel_amount, refuel_attempts, player_id))
            connection.commit()
            return True

        else:
            print("Player not found.")
            return False

    except Exception as e:
        print(f"Failed to refuel: {e}")
        return False

# Game logic for calculating and updating player fuel units
def refuel_action(connection, player_id):
    cursor = connection.cursor()

    # Maximum allowed refuel attempts
    MAX_REFUEL_ATTEMPTS = 5

    # Retrieve player's current fuel level and refuel attempts
    cursor.execute("SELECT fuel_units, refuel_attempts FROM player WHERE player_id = %s", (player_id,))
    player_data = cursor.fetchone()

    if not player_data:
        print("Player data not found.")
        return False

    current_fuel = player_data[0]
    refuel_attempts = player_data[1]

    # Check if the player has exceeded the maximum number of refuel attempts
    if refuel_attempts >= MAX_REFUEL_ATTEMPTS:
        print(f"You have no remaining refuel attempts. Maximum refuel attempts ({MAX_REFUEL_ATTEMPTS}) reached.")
        return "game_over"

    # Retrieve player's current airport ID
    cursor.execute("SELECT current_airport_id FROM player WHERE player_id = %s", (player_id,))
    result = cursor.fetchone()
    if not result:
        print("Player or current location not found.")
        return False

    current_airport_id = result[0]

    # Fetch the fuel price at the current airport
    cursor.execute("SELECT fuel_price FROM airport WHERE id = %s", (current_airport_id,))
    fuel_data = cursor.fetchone()
    if not fuel_data or fuel_data[0] is None:
        print("Fuel is not available at this airport.")
        return False

    fuel_price = fuel_data[0]
    print(f"Fuel price at current airport: {fuel_price:.2f} per unit.")

    try:
        # Ask the player for the amount of fuel they wish to buy
        fuel_units_to_buy = int(input("Enter the number of fuel units you want to buy: "))
        if fuel_units_to_buy > 1000:
            print("You cannot refuel more than 1000 units in a single session.")
            return False

        # Calculate the total fuel units after refueling
        total_fuel = current_fuel + fuel_units_to_buy

        # Confirm the transaction
        confirm = input(f"Do you want to buy {fuel_units_to_buy} units of fuel? (yes/no): ")
        if confirm.lower() == 'yes':
            # Perform the refueling and update refuel attempts
            new_refuel_attempts = refuel_attempts + 1

            # Update player's fuel and refuel attempts in the database
            cursor.execute(
                "UPDATE player SET fuel_units = %s, refuel_attempts = %s WHERE player_id = %s",
                (total_fuel, new_refuel_attempts, player_id)
            )
            connection.commit()

            print("Refueling successful!")
            return True

        else:
            print("Refueling cancelled.")
            return False

    except ValueError:
        print("Invalid input. Please enter a valid number.")
        return False

# Check if player has lost the game
def check_game_over(connection, player_id):
    cursor = connection.cursor()

    # Fetch the player's current fuel level and refuel attempts
    cursor.execute("SELECT fuel_units, refuel_attempts FROM player WHERE player_id = %s", (player_id,))
    result = cursor.fetchone()

    if result:
        current_fuel, refuel_attempts = result

        # Check if the player has no fuel left and no refuel attempts left
        if current_fuel <= 0 and refuel_attempts <= 0:
            print("Game over: No fuel and no refuel attempts left.")
            return True
        else:
            return False
    else:
        print("Player data not found.")
        return False


# using geopy to calculating the distance
from geopy.distance import geodesic

def calculate_distance(lat1, lon1, lat2, lon2):
    start = (lat1, lon1)
    end = (lat2, lon2)

    return geodesic(start, end).kilometers


# Calculating the distance within the game
def travel_to_new_airport(connection, player_id, current_airport_id, destination_airport_id, game_id):
    cursor = connection.cursor()

    # Fetch coordinates of both airports
    cursor.execute("SELECT latitude_deg, longitude_deg FROM airport WHERE id = %s", (current_airport_id,))
    current_airport = cursor.fetchone()

    cursor.execute("SELECT latitude_deg, longitude_deg FROM airport WHERE id = %s", (destination_airport_id,))
    destination_airport = cursor.fetchone()

    if current_airport and destination_airport:
        # Calculate the distance between airports
        distance = geodesic((current_airport[0], current_airport[1]), (destination_airport[0], destination_airport[1])).kilometers
        fuel_consumption_rate = 0.5  # Example rate: 0.5 fuel units per kilometer
        required_fuel = distance * fuel_consumption_rate

        # Get player's current fuel level
        cursor.execute("SELECT fuel_units FROM player WHERE player_id = %s", (player_id,))
        player_data = cursor.fetchone()
        if not player_data:
            print("Player data not found.")
            return False

        current_fuel = player_data[0]

        # Check if the player has enough fuel to travel
        if current_fuel < required_fuel:
            print(f"Not enough fuel. You need {required_fuel:.2f} units but only have {current_fuel:.2f} units.")
            return False  # Not enough fuel, prevent the player from traveling

        # Deduct fuel and update player's fuel level
        new_fuel_level = current_fuel - required_fuel
        cursor.execute("UPDATE player SET fuel_units = %s WHERE player_id = %s", (new_fuel_level, player_id))
        connection.commit()

        # Insert the movement into the player_movements table
        cursor.execute(
            "INSERT INTO player_movement (player_id, departure_airport_id, destination_airport_id, distance_traveled) "
            "VALUES (%s, %s, %s, %s)",
            (player_id, current_airport_id, destination_airport_id, distance)
        )
        connection.commit()

        # **Update player's location using the update_player_location() function**
        update_successful = update_player_location(connection, player_id, destination_airport_id)
        if not update_successful:
            print("Error updating player location.")
            return False

        # Update move count in the game_state
        cursor.execute("SELECT moves_count FROM game_state WHERE game_id = %s", (game_id,))
        game_data = cursor.fetchone()
        if game_data:
            current_move_count = game_data[0]
            new_move_count = current_move_count + 1

            # Call the update_game_state() function to update the move count
            update_game_state(connection, game_id, player_id, moves_count=new_move_count)
        return True
    else:
        print("Invalid airport ID.")
        return False


# Plyer option for traveling to a new location
def choose_destination_and_travel(connection, player_id, game_id):  # Added game_id parameter
    cursor = connection.cursor()

    # The ID of the airport where the player wins the game
    FUGITIVE_AIRPORT_ID = 15

    # Retrieve the current airport ID for the player
    cursor.execute("SELECT current_airport_id FROM player WHERE player_id = %s", (player_id,))
    result = cursor.fetchone()
    if result:
        current_airport_id = result[0]
    else:
        print("Failed to retrieve current airport ID for player:", player_id)
        return False

    # List available airports (except the current airport)
    airports = list_all_airports_except_current(connection, current_airport_id)
    if airports:
        while True:
            print("Available Airports:")
            for index, airport in enumerate(airports, start=1):
                print(f"{index}. {airport[1]} ({airport[2]})")

            # Ask player to select a destination
            choice = input("Select the airport number to travel to (or type 'cancel' to go back to the main menu): ")
            if choice.lower() == 'cancel':
                print("Returning to the main menu.")
                return False

            if choice.isdigit() and 1 <= int(choice) <= len(airports):
                destination_airport_id = airports[int(choice) - 1][0]

                # Calculate the distance and required fuel
                cursor.execute("SELECT latitude_deg, longitude_deg FROM airport WHERE id = %s", (current_airport_id,))
                current_airport = cursor.fetchone()

                cursor.execute("SELECT latitude_deg, longitude_deg FROM airport WHERE id = %s", (destination_airport_id,))
                destination_airport = cursor.fetchone()

                if current_airport and destination_airport:
                    # Calculate distance using geodesic
                    distance = geodesic((current_airport[0], current_airport[1]), (destination_airport[0], destination_airport[1])).kilometers
                    fuel_consumption_rate = 0.5
                    required_fuel = distance * fuel_consumption_rate

                    # Display the distance and required fuel to the player
                    print(f"Distance to {airports[int(choice)-1][1]}: {distance:.2f} Km")
                    print(f"Required fuel to reach destination: {required_fuel:.2f} units")

                    # Ask the player if they want to proceed with travel or go back
                    confirm = input("Do you want to travel to this airport? (yes/no): ").strip().lower()

                    if confirm == 'yes':
                        # First, travel to the new airport, handle fuel in travel_to_new_airport
                        travel_successful = travel_to_new_airport(connection, player_id, current_airport_id, destination_airport_id, game_id)  # Pass game_id here
                        if travel_successful:
                            print(f"Successfully traveled to {airports[int(choice)-1][1]}.")

                            # Check if the player is traveling to the winning airport
                            if destination_airport_id == FUGITIVE_AIRPORT_ID:
                                print("Congratulations! You've caught the fugitive and won the game!")
                                update_game_state(connection, game_id, player_id, criminal_caught=True, game_over=True)
                                return True
                            else:
                                # Provide feedback for wrong airport
                                print(f"You've arrived at {airports[int(choice) - 1][1]}, but the fugitive is not here. Keep searching!")
                                return False
                        else:
                            print(f"Travel to {airports[int(choice)-1][1]} failed. You do not have enough fuel.")
                            return False
                    elif confirm == 'no':
                        print("You canceled traveling. Select another airport.")
                    else:
                        print("Invalid input. Please enter 'yes' or 'no'.")
                else:
                    print("Error fetching airport coordinates. Please try again.")
            else:
                print("Invalid choice. Please select a valid airport number.")
    else:
        print("No available destinations.")
        return False


# Player interaction with npcs and clues
def interact_with_npcs_and_clues(connection, player_id):
    cursor = connection.cursor()
    cursor.execute("SELECT current_airport_id FROM player WHERE player_id = %s", (player_id,))
    result = cursor.fetchone()
    if result:
        current_airport_id = result[0]
        # Get clues for the current airport
        clues = get_clues_by_airport(connection, current_airport_id)
        if clues:
            print("\nAvailable Clues at this Airport:")
            for clue in clues:
                print(f"Description: {clue[0]}")
        else:
            print("No clues available at this airport.")

        # Get NPCs at the current airport
        npcs = get_npcs_by_airport(connection, current_airport_id)
        if npcs:
            print("\nNPCs available to talk to:")
            for npc in npcs:
                print(f"Name: {npc[0]}, Role: {npc[1]}, Info: {npc[2]}")
        else:
            print("No NPCs are available to interact with at this airport.")
    else:
        print("Player location is not available.")











