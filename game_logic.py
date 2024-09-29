from queries import (get_fuel_info_at_airport, get_player_fuel, update_player_fuel, calculate_fuel_requirement, get_airport_name,
                     update_player_location, get_clues_by_airport, get_npcs_by_airport, list_all_airports_except_current, start_new_game)
from decimal import Decimal

# Game logic for player refueling
def refuel_player(connection, player_id, fuel_to_add):
    cursor = connection.cursor()
    try:
        # Fetch the current fuel level
        cursor.execute("SELECT fuel_units FROM player WHERE player_id = %s", (player_id,))
        result = cursor.fetchone()
        if result:
            current_fuel = result[0]
            new_fuel_amount = current_fuel + fuel_to_add
            if new_fuel_amount > 2147483647:
                print("Fuel amount exceeds the maximum allowed value. Cannot refuel this much.")
                return False

            # Update the fuel level
            cursor.execute("UPDATE player SET fuel_units = %s WHERE player_id = %s", (new_fuel_amount, player_id))
            connection.commit()
            print(f"Refueled successfully! New fuel amount: {new_fuel_amount} units.")
            return True
        else:
            print("Player not found.")
            return False
    except Exception as e:
        print(f"Failed to refuel: {e}")
        return False


def refuel_action(connection, player_id):
    cursor = connection.cursor()

    # Retrieve the player's current airport ID
    cursor.execute("SELECT current_airport_id FROM player WHERE player_id = %s", (player_id,))
    result = cursor.fetchone()
    if not result:
        print("Player or current location not found.")
        return

    current_airport_id = result[0]

    # Fetch the fuel price at the current airport
    cursor.execute("SELECT fuel_price FROM airport WHERE id = %s", (current_airport_id,))
    fuel_data = cursor.fetchone()
    if not fuel_data or fuel_data[0] is None:
        print("Fuel is not available at this airport.")
        return

    fuel_price = fuel_data[0]
    print(f"Fuel price at current airport: {fuel_price:.2f} per unit.")

    try:
        # Ask the player for the amount of fuel they wish to buy
        fuel_units_to_buy = int(input("Enter the number of fuel units you want to buy: "))
        if fuel_units_to_buy <= 0:
            print("Invalid input. Number of fuel units must be positive.")
            return

        total_cost = fuel_units_to_buy * fuel_price
        print(f"Total cost to refuel: {total_cost:.2f} for {fuel_units_to_buy} units of fuel.")

        # Confirm the transaction
        confirm = input(f"Do you want to buy {fuel_units_to_buy} units of fuel for {total_cost:.2f}? (yes/no): ")
        if confirm.lower() == 'yes':
            if refuel_player(connection, player_id, fuel_units_to_buy):
                print("Refueling successful!")
            else:
                print("Refueling failed.")
        else:
            print("Refuel cancelled.")
    except ValueError:
        print("Invalid input. Please enter a valid number.")



# using geopy to calculating the distance
from geopy.distance import geodesic

def calculate_distance(lat1, lon1, lat2, lon2):
    start = (lat1, lon1)
    end = (lat2, lon2)

    return geodesic(start, end).kilometers

# Game logic for calculating the distance within the game
def travel_to_new_airport(connection, player_id, current_airport_id, destination_airport_id):
    cursor = connection.cursor()

    # Fetch coordinates of both airports
    cursor.execute("SELECT latitude_deg, longitude_deg FROM airport WHERE id = %s", (current_airport_id,))
    current_airport = cursor.fetchone()

    cursor.execute("SELECT latitude_deg, longitude_deg FROM airport WHERE id = %s", (destination_airport_id,))
    destination_airport = cursor.fetchone()

    if current_airport and destination_airport:
        # Calculate distance between airports
        distance = calculate_distance(current_airport[0], current_airport[1], destination_airport[0], destination_airport[1])
        print(f"Distance between airports: {distance:.2f} Km")  # Debug print

        # Calculate fuel required
        fuel_consumption_rate_per_km = 0.5
        fuel_required = distance * fuel_consumption_rate_per_km
        print(f"Required fuel: {fuel_required:.2f} units.")  # Debug print

        # Get player's current fuel level
        cursor.execute("SELECT fuel_units FROM player WHERE player_id = %s", (player_id,))
        current_fuel = cursor.fetchone()

        if current_fuel and current_fuel[0] >= fuel_required:
            # Deduct fuel and update player's location
            new_fuel_level = current_fuel[0] - Decimal(fuel_required)
            cursor.execute("UPDATE player SET fuel_units = %s WHERE player_id = %s", (new_fuel_level, player_id))
            connection.commit()
            return True
        else:
            print(f"Not enough fuel. You need {fuel_required:.2f} units but only have {current_fuel[0]} units.")
            return False
    else:
        print("Invalid airport ID.")  # Ensure this logic is valid
        return False


def present_information_and_decide(connection, current_airport_id, visited_airports, correct_airport_id):
    print("You've arrived at the airport. Gathering clues and meeting people.")
    clues = get_clues_by_airport(connection, current_airport_id)
    npcs = get_npcs_by_airport(connection, current_airport_id)

    print("\nDiscovered Clues:")
    for clue in clues:
        print(f"- {clue[0]} (Validity: {clue[1]})")

    print("\nPeople you met:")
    for npc in npcs:
        print(f"- {npc[0]}, {npc[1]} says: {npc[2]}")

    print("\nAvailable Airports for Travel:")
    remaining_airports = list_all_airports_except_current(connection, current_airport_id)
    if not remaining_airports:
        print("No other airports available to travel to.")
        return None, visited_airports

    # Display airports with correct indexing for user selection
    for idx, airport in enumerate(remaining_airports, start=1):
        print(f"{idx}. {airport[0]} in {airport[1]}")

    # Input handling with error checking
    try:
        choice = int(input("Enter your choice (number): ")) - 1
        if choice < 0 or choice >= len(remaining_airports):
            raise ValueError("Invalid airport choice. Please select a valid number.")
    except ValueError as ve:
        print(str(ve))
        return None, visited_airports

    chosen_destination = remaining_airports[choice]
    print(f"\nYou decide to travel to: {chosen_destination[0]} in {chosen_destination[1]}")

    # Validate the chosen destination
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM airport WHERE name = %s AND iso_country = (SELECT iso_country FROM country WHERE name = %s)", (chosen_destination[0], chosen_destination[1]))
    result = cursor.fetchone()
    if result:
        chosen_destination_id = result[0]
        # print(f"Chosen airport ID: {chosen_destination_id}")
        visited_airports.append(chosen_destination_id)

        if chosen_destination_id == correct_airport_id:
            print("\nYou made the correct decision! You're closer to catching the criminal.")
        else:
            print("\nYou've made a wrong turn. Try gathering more clues at a new airport.")

        return chosen_destination_id, visited_airports
    else:
        print("Error: Could not find the airport in the database.")
        return None, visited_airports


def choose_destination_and_travel(connection, player_id):
    cursor = connection.cursor()

    # Retrieve the current airport ID for the player
    cursor.execute("SELECT current_airport_id FROM player WHERE player_id = %s", (player_id,))
    result = cursor.fetchone()
    if result:
        current_airport_id = result[0]
    else:
        print("Failed to retrieve current airport ID for player:", player_id)
        return

    # List available airports (except current airport)
    airports = list_all_airports_except_current(connection, current_airport_id)
    if airports:
        print("Available Airports:")
        for index, airport in enumerate(airports, start=1):
            print(f"{index}. {airport[1]} ({airport[2]})")  # Adjusting to the correct tuple indices

        # Ask player to select a destination
        choice = input("Select the airport number to travel to: ")
        if choice.isdigit() and 1 <= int(choice) <= len(airports):
            destination_airport_id = airports[int(choice) - 1][0]
            print(f"Selected Airport ID: {destination_airport_id}")  # Debug print
            # Call travel_to_new_airport to process travel
            if travel_to_new_airport(connection, player_id, current_airport_id, destination_airport_id):
                # Successfully traveled, now update player location details
                update_player_location(connection, player_id, destination_airport_id)
            else:
                print("Travel failed due to insufficient fuel. Please refuel before attempting to travel.")
        else:
            print("Invalid choice, please try again.")
    else:
        print("No available destinations.")


def interact_with_npcs_and_clues(connection, player_id):
    cursor = connection.cursor()
    # Retrieve the current airport ID from the player's location
    cursor.execute("SELECT current_airport_id FROM player WHERE player_id = %s", (player_id,))
    result = cursor.fetchone()
    if result:
        current_airport_id = result[0]
        # Get clues for the current airport
        clues = get_clues_by_airport(connection, current_airport_id)
        if clues:
            print("\nAvailable Clues at this Airport:")
            for clue in clues:
                print(f"Description: {clue[0]}, Validity: {clue[1]}")
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











