
# Server for forum and games

This server serves requests from users and responds with pages depending on the user's status. Users can register or log in if they are already in the server's database. The database is organized with SQLite and stores basic information about the users.

After logging in, users can send messages to the forum or directly to other people. Messages are stored in one place with basic encryption. Users can also receive messages from other users.

The program includes a Tic-Tac-Toe game where users can play with a basic AI or another user. To start playing, you need to know the ID of the game. To start a game with the AI, you just need to click on the game or use the game ID with "ai".

Additionally, there is a Blackjack game where users can play with a dealer. You will be playing for money, but if your wallet balance falls below 10, you will be automatically redirected to a page to add more money.

If a user is inactive, a logout process will start with a warning about the inactivity.
