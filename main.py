from db_connection import connect_to_database, close_connection
from queries import get_or_create_player, start_new_game, show_player_status
from game_logic import choose_destination_and_travel, refuel_action, interact_with_npcs_and_clues, travel_to_new_airport


def main():
    connection = connect_to_database()
    if connection is None:
        print("Failed to connect to the database.")
        return

    print("Welcome to Operation Skytrack!")
    player_id = get_or_create_player(connection)

    if not player_id:
        print("No player selected. Exiting the game.")
        return

    game_id = start_new_game(connection, player_id)

    while True:
        print("\nMain Menu:")
        print("1. Travel to another airport")
        print("2. Refuel")
        print("3. Check clues and interact with NPCs")
        print("4. View Player Status")  # New option to view status
        print("5. End the game")
        choice = input("What would you like to do? ")

        if choice == "1":
            choose_destination_and_travel(connection, player_id)
        elif choice == "2":
            refuel_action(connection, player_id)
        elif choice == "3":
            interact_with_npcs_and_clues(connection, player_id)
        elif choice == "4":
            show_player_status(connection, player_id)  # Show status option
        elif choice == "5":
            print("Thanks for playing!")
            break
        else:
            print("Invalid choice, please try again.")

    close_connection(connection)


if __name__ == "__main__":
    main()







