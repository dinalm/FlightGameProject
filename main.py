from db_connection import connect_to_database, close_connection
from queries import get_or_create_player, start_new_game, show_player_status, update_game_state
from game_logic import choose_destination_and_travel, refuel_action, interact_with_npcs_and_clues, check_game_over


def main():

    connection = connect_to_database()
    if connection is None:
        print("Failed to connect to the database.")
        return

    print("Welcome to Operation Skytrack!")

    # Create or retrieve player profile
    player_id = get_or_create_player(connection)
    if not player_id:
        print("No player selected. Exiting the game.")
        close_connection(connection)

    # Start a new game
    game_id = start_new_game(connection, player_id)
    if not game_id:
        print("Failed to start a new game. Exiting the game.")
        close_connection(connection)

    # Main game loop
    while True:
        print("\nMain Menu:")
        print("1. Travel to another airport")
        print("2. Refuel")
        print("3. Check clues and interact with NPCs")
        print("4. View Player Status")
        print("5. End the game")

        choice = input("What would you like to do? ")

        if choice == "1":
            # Handle traveling
            travel_successful = choose_destination_and_travel(connection, player_id, game_id)

            if travel_successful:
                print("!-------------------Congratulations!-------------------!")
                update_game_state(connection, game_id, player_id, criminal_caught=True, game_over=True)
                break

            if check_game_over(connection, player_id):
                print("!----------------GAME OVER------------------!")
                update_game_state(connection, game_id, player_id, game_over=True)
                break

        elif choice == "2":
            # Handle refueling
            refuel_result = refuel_action(connection, player_id)

            if refuel_result == "game_over":
                print("!----------------GAME OVER------------------!")
                update_game_state(connection, game_id, player_id, game_over=True)
                break

            elif not refuel_result:
                if check_game_over(connection, player_id):
                    print("!----------------GAME OVER------------------!")
                    update_game_state(connection, game_id, player_id, game_over=True)
                    break

        elif choice == "3":
            # Handle NPC interaction
            interact_with_npcs_and_clues(connection, player_id)

            if check_game_over(connection, player_id):
                print("!----------------GAME OVER------------------!")
                update_game_state(connection, game_id, player_id, game_over=True)
                break

        elif choice == "4":
            show_player_status(connection, player_id)

        elif choice == "5":
            print("Thanks for playing!")
            update_game_state(connection, game_id, player_id, game_over=True)
            break

        else:
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    main()
