from queries import (get_fuel_info_at_airport, get_player_fuel, update_player_fuel, calculate_fuel_requirement, get_airport_name,
                     update_player_location, get_clues_by_airport, get_npcs_by_airport, list_all_airports_except_current, start_new_game)
from decimal import Decimal

# Game logic for player refueling
def refuel_player(connection, player_id, airport_id, fuel_units_to_buy):
    airport_name, fuel_price = get_fuel_info_at_airport(connection, airport_id)
    if fuel_price == Decimal('0.0'):
        print(f"No fuel available at {airport_name if airport_name else 'airport with ID ' + str(airport_id)}.")
        return False

    # Convert fuel_units_to_buy to Decimal for precision in calculations
    fuel_units_to_buy = Decimal(fuel_units_to_buy)
    total_cost = fuel_units_to_buy * fuel_price
    print(f"Fuel price at {airport_name}: {fuel_price:.2f} per unit.")
    print(f"Total cost to refuel: {total_cost:.2f} for {fuel_units_to_buy} units of fuel.")

    current_fuel = get_player_fuel(connection, player_id)
    if current_fuel is not None:
        new_fuel_amount = current_fuel + fuel_units_to_buy
        update_player_fuel(connection, player_id, new_fuel_amount)
        print(f"Refueled {fuel_units_to_buy} units at {airport_name}. New fuel amount: {new_fuel_amount:.2f} units.")
        return True
    else:
        print("Failed to retrieve current fuel amount. Refueling is not possible.")
    return False


def refuel_action(connection, player_id):
    cursor = connection.cursor()

    # Retrieve player's current airport ID
    cursor.execute("SELECT current_airport_id FROM player WHERE player_id = %s", (player_id,))
    result = cursor.fetchone()
    if result:
        current_airport_id = result[0]
    else:
        print("Player or current location not found.")
        return

    # Check if fuel is available at the current airport and get the fuel price
    cursor.execute("SELECT fuel_price, name, fuel_availability FROM airport WHERE id = %s", (current_airport_id,))
    airport_data = cursor.fetchone()
    if airport_data:
        fuel_price, airport_name, fuel_availability = airport_data
        if fuel_availability == 0 or fuel_price == Decimal('0.0'):
            print(f"No fuel available at {airport_name}.")
            return
        # Convert Decimal to float for arithmetic operation
        fuel_price = float(fuel_price)
    else:
        print("Airport not found.")
        return

    print(f"Fuel price at {airport_name}: {fuel_price:.2f} per unit.")

    try:
        # Prompt player to input how much fuel they want to buy
        fuel_units_to_buy = float(input("Enter the number of fuel units you want to buy: "))
        if fuel_units_to_buy <= 0:
            print("Invalid input. You must enter a positive number.")
            return

        # Calculate the total cost of fuel
        total_cost = fuel_units_to_buy * fuel_price
        print(f"Total cost to refuel: {total_cost:.2f} for {fuel_units_to_buy} units of fuel.")

        # Confirm the purchase
        confirm = input(f"Do you want to buy {fuel_units_to_buy:.2f} units of fuel for {total_cost:.2f}? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Refuel cancelled.")
            return

        # Call the refuel_player function with the amount of fuel to buy
        if refuel_player(connection, player_id, current_airport_id, fuel_units_to_buy):
            print("Refueling successful!")
        else:
            print("Refueling failed.")

    except ValueError:
        print("Invalid input. Please enter a valid number for fuel units.")


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
        distance = geodesic((current_airport[0], current_airport[1]), (destination_airport[0], destination_airport[1])).kilometers
        print(f"Distance between airports: {distance:.2f} Km")

        # Calculate fuel required
        fuel_consumption_rate = 0.5  # Example rate: 0.5 fuel units per km
        required_fuel = distance * fuel_consumption_rate
        print(f"Required fuel: {required_fuel:.2f} units.")

        # Get player's current fuel level
        cursor.execute("SELECT fuel_units FROM player WHERE player_id = %s", (player_id,))
        current_fuel = cursor.fetchone()

        if current_fuel and current_fuel[0] >= required_fuel:
            # Deduct fuel and update player's location
            new_fuel_level = current_fuel[0] - required_fuel
            cursor.execute("UPDATE player SET fuel_units = %s, current_airport_id = %s WHERE player_id = %s",
                           (new_fuel_level, destination_airport_id, player_id))
            connection.commit()
            print(f"Travel successful! New fuel level: {new_fuel_level:.2f} units.")
            return True
        else:
            print(f"Not enough fuel. You need {required_fuel:.2f} units but only have {current_fuel[0]:.2f} units.")
            return False
    else:
        print("Invalid airport ID.")
        return False


def execute_move(connection, player_id, current_airport_id, destination_airport_id):
    # Calculate required fuel for the next journey
    required_fuel = calculate_fuel_requirement(current_airport_id, destination_airport_id, connection)

    # Check current fuel level
    current_fuel = get_player_fuel(connection, player_id)

    if current_fuel >= required_fuel:
        # Update player location and fuel
        update_player_location(connection, player_id, destination_airport_id)
        update_player_fuel(connection, player_id, current_fuel - required_fuel)

        print(
            f"Travelled successfully to {get_airport_name(connection, destination_airport_id)}. Remaining fuel: {current_fuel - required_fuel}.")
        return True
    else:
        print("Insufficient fuel for this journey.")
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
            # airport[0] is the airport name, airport[1] is the country name
            print(f"{index}. {airport[0]} ({airport[1]})")

        # Ask player to select a destination
        choice = input("Select the airport number to travel to: ")
        if choice.isdigit() and 1 <= int(choice) <= len(airports):
            destination_airport_id = airports[int(choice) - 1][0]
            # Call travel_to_new_airport to process travel
            if not travel_to_new_airport(connection, player_id, current_airport_id, destination_airport_id):
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











