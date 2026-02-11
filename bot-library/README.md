# CopperHead Bot Library

This folder contains bots contributed by participants in CopperHead Bot Hack Tournaments. Feel free to use these bots as inspiration or starting points for your own AI opponents!

Submit your own bot by creating a pull request with your bot file added to this directory or contained in a sub-directory. Please include a brief description of your bot's strategy in the PR description.

See [Building-Your-Own-Bot.md](../Building-Your-Own-Bot.md) for instructions on building a bot for CopperHead.

## Included Bots

* [`murderbot.py`](murderbot.py) Aggressively chases down the opponent to try and cause a collision. By @nonfamousd

## Bot requirements

To be included in the bot library, bots must meet the requirements below.

### License

Bots must be open source software under the MIT License. 

### Arguments

Bots must accept the following arguments:

* `--server` (required): WebSocket URL of the server to connect to (e.g., `ws://localhost:8765/ws` or `wss://your-codespaces-url.app.github.dev/ws/`). This should match the URL displayed in the game client.
* `--name` (optional): Overrides the default name of the bot player. Give your bot a unique default name!
* `--difficulty` (optional): Difficulty level (1-10, 10 is hardest) that the bot can use to adjust its strategy. It is not required that the bot change its behavior, but this argument must be accepted if provided.

### Interactions with server

* Bots should connect to the server, wait until they are added to a match, play the game until the tournament ends, and then terminate. 

* Bots should signal ready immediately at the beginning of each game.




