# Build your own CopperHead bot

We encourage developers to build their own AI-controlled CopperHead bots to play with or to compete against other humans and bots in CopperBot Competitions. Bots can be developed in any programming language that supports WebSocket communication, and can easily be created without programming experience using tools like GitHub Copilot.

Follow the guide in the [copperhead-bot](https://github.com/revodavid/copperhead-bot) repository to get started.

The default CopperBot AI opponent, which is launched as needed by the server at 10 difficulty levels, is implemented in the file [`copperbot.py`](copperbot.py) in this repository.

Bots communicate with the server via the API documented at [API.md](API.md). For details on game rules and competition logic, see [game-rules.md](game-rules.md) and [competition-logic.md](competition-logic.md).

A test suite to validate bot communication with the server is provided in the [`copperhead-bot`](https://github.com/revodavid/copperhead-bot) repository in the `tests` folder. You can run this test suite against your bot during development to ensure it can successfully connect and play a game on the server.
