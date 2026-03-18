# Participating in a CopperHead Bot Hack Tournament

Welcome to this CopperHead Bot Hack Tournament! You and your team will build an AI bot to play a 2-player variant of the Snake game, then compete against other teams' bots in a knockout tournament. No prior programming experience is required — AI coding assistants like [GitHub Copilot](https://github.com/features/copilot) can help you build a competitive bot from scratch.

Your host will provide you with a link to access the CopperHead client web app to access the game server used for this tournament. Open the link to get started and try out the game if you're new to CopperHead.

### What you'll need ###

- A name for your team.
- A laptop with a web browser and internet access. (Any laptop will do.)
- A [GitHub](https://github.com) account (a free account includes access to GitHub Copilot and Codespaces, and will suffice).
- The tournament **server URL**. You can find this on the Lobby screen of the CopperHead client.
- The server settings file **`server-settings.json`**. You can download this file from the CopperHead client.

### Don't want to code?

You can still join in! Help your team by suggesting strategies and testing bots as a human opponent during the hacking period.

If allowed by your Host, you can also test your reflexes and compete against bot players in the final tournament. Human players can join at the host-provided CopperHead Client link by clicking "Join Lobby".

## Step 1: Set up your development environment

Fork the [copperhead-bot](https://github.com/revodavid/copperhead-bot) repository to your own GitHub account. Then, launch your fork in GitHub Codespaces. This will be your environment for developing your bot and launching it to play on the game server.

 * To launch a GitHub repository in CodeSpaces, click the green **Code** button, then click the **Codespaces** tab and click "Create CodeSpace on main".

## Step 2: Build your bot

Use the file `mybot.py` in the copperhead-bot repository as a starting point for your bot. You can change the file name if you want, but definitely change the bot name in the code to match your team name, so the Host can recognize your bot during the tournament.

### Using AI to help you code

You don't need to be an expert programmer to build a winning bot. AI coding assistants can do the heavy lifting:

- [**GitHub Copilot**](https://github.com/features/copilot) works right in the GitHub web interface — no code editor required.
- [**GitHub Copilot CLI**](https://github.com/features/copilot/cli/) can generate code from natural language prompts, even if you've never programmed before. You can run `copilot` from the terminal in Codespaces, or install it on your laptop and run it on the cloned repository.
- [**GitHub Copilot in Visual Studio Code**](https://code.visualstudio.com/docs/editor/github-copilot) offers an enhanced coding experience with suggestions and autocompletion.
- Use any AI assistant or IDE you like! See how your favorite tool fares in the competition.

Review the [copperhead-bot repository](https://github.com/revodavid/copperhead-bot) for tips and inspiration for building your bot.

### Manually coding your bot

See [How-To-Build-Your-Own-Bot.md](How-To-Build-Your-Own-Bot.md) for  instructions on coding a bot.

You can find other bots for inspiration in the `bot-library` directory of the [copperhead-server](https://github.com/revodavid/copperhead-server) repository. 

## Step 3 (optional): Launch a private server for bot testing

Before you unleash your bot on the tournament server, you can test it on your own private server in Codespaces. This is a great way to iterate quickly and see how your bot performs against the default CopperBot opponent or human players on your team.

1. Visit the [copperhead-server](https://github.com/revodavid/copperhead-server) repository and launch it in GitHub Codespaces. This will give you a personal game server to test your bot against during development.

2. Replace the `server-settings.json` file in your fork with the one provided by the Host. This ensures your bot is tuned to the correct game rules (grid size, speed, fruit types, etc.).

> **TIP:** You can restart your server at any time by modifying and saving the `server-settings.json` file. For testing, consider setting the `arenas` parameter to 1 for a single-round tournament.

3. Launch the CopperHead client on your team server using the "Play Now" link shown in Codespaces.

## Step 4: Test your bot

If your host allows it, you can launch your bot on the Host's tournament server during the hacking period to test against other teams' bots. Otherwise, use a private server as described in Step 3 to test against the default CopperBot opponent or human players on your team.

Open the terminal in the `copperhead-bot` Codespace and run your bot with the tournament server URL provided or your private server URL:

To test your bot on a server, run the following command in the terminal:

1. Run your bot against the server:
    ```bash
    python hackbot.py --name "TeamName Bot" --server wss://your-codespaces-url.app.github.dev/ws/
    ```
   - Find the server URL in the Server Settings section of the client lobby screen. It starts with `wss://`.
   - Replace the file name `hackbot.py` with your bot's file name, if different.
   - You can skip the `--name` parameter if your bot already assigns itself a name in code.

2. Open the client to see your bot in the Lobby. If you need an opponent, either click "Join Lobby" as a human, launch a second instance of your bot, or click "Add Bot" to add a CopperBot opponent.

3. Click "Observe" to watch your bot play. Tweak your bot code and re-run to improve its performance.

## Step 4: Compete in the Final Tournament

When the Host announces the hacking period is over, it's time for the knockout tournament.

1. Connect your bot to the Host's public tournament server:
    ```bash
    python hackbot.py --name "TeamName Bot" --server wss://host-codespaces-url.app.github.dev/ws/
    ```

2. Once all teams have joined, the tournament begins automatically. Watch the action on the big screen as bots battle in knockout rounds!

3. The last bot (or human) standing wins the tournament. 🏆

## Step 5: Save your bot

Don't forget to save your work! Commit your bot to your forked repository from the Source Control panel in Codespaces, or via the terminal:

```bash
git add .
git commit -m "My hack tournament bot"
git push
```

If you're on a free GitHub account, consider deleting your Codespace afterward to save your free hours. You can manage Codespaces at https://github.com/codespaces.

If you built something awesome, consider submitting a pull request to add your bot to the [bot-library](bot-library) directory for others to learn from!

## Have fun!

We hope you have a great time at the tournament! If you have feedback or stories to share, please open an issue in the [copperhead-server](https://github.com/revodavid/copperhead-server) repository.
