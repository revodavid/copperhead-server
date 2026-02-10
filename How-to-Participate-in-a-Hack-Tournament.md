# Participating in a CopperHead Bot Hack Tournament

Welcome to a CopperHead Bot Hack Tournament! You and your team will build an AI bot to play Snake, then compete against other teams' bots in a knockout tournament. No prior programming experience is required — AI coding assistants like [GitHub Copilot](https://github.com/features/copilot) can help you build a competitive bot from scratch.

**What you'll need**:
- A [GitHub](https://github.com) account (a free account includes access to GitHub Copilot and Codespaces, and will suffice)
- A laptop with a web browser and internet access
- Your team name
- The tournament **server URL** and **`server-settings.json`** file from your Host

## Step 1: Set up your development environment

1. Fork the [copperhead-server](https://github.com/revodavid/copperhead-server) repository to your own GitHub account.

2. Replace the `server-settings.json` file in your fork with the one provided by the Host. This ensures your bot is tuned to the correct game rules (grid size, speed, fruit types, etc.).

3. Launch your fork in GitHub Codespaces. (Click the green **Code** button, then click the **Codespaces** tab.) This gives you a personal game server for development and testing — no local installation required.

> **TIP:** You can restart your server at any time by modifying and saving the `server-settings.json` file.

## Step 2: Build your bot

Create a file called `hackbot.py` for your bot. A great starting point is to copy the default `copperbot.py` file from the repository and modify it. You can also find other bots for inspiration in the `bot-library` directory.

Make sure your bot assigns itself a name matching your team name!

### Writing your bot

See [Building-Your-Own-Bot.md](Building-Your-Own-Bot.md) for detailed instructions on building a bot. The [Game Rules](game-rules.md) and [Competition Logic](competition-logic.md) documents are also useful references.

### Using AI to help you code

You don't need to be an expert programmer to build a winning bot. AI coding assistants can do the heavy lifting:

- [**GitHub Copilot**](https://github.com/features/copilot) works right in the GitHub web interface — no code editor required.
- [**GitHub Copilot CLI**](https://github.com/features/copilot/cli/) can generate code from natural language prompts, even if you've never programmed before.
- [**GitHub Copilot in Visual Studio Code**](https://code.visualstudio.com/docs/editor/github-copilot) offers an enhanced coding experience with suggestions and autocompletion.
- Use any AI assistant or IDE you like! See how your favorite tool fares in the competition.

### Don't want to code?

You can still join in! Help your team by suggesting strategies and testing bots as a human opponent during the hacking period. You can also test your reflexes and compete against bot players in the final tournament.

## Step 3: Test your bot

Launch the CopperHead client on your team server using the "Play Now" link shown in Codespaces.

To test your bot:

1. Run your bot against your team's server:
    ```bash
    python hackbot.py --name "TeamName Bot" --server wss://your-codespaces-url.app.github.dev/ws/
    ```
   - Find the server URL in the Codespaces terminal output, or at the bottom of the client lobby screen.
   - You can skip `--name` if your bot already assigns itself a name in code.

2. Add an opponent: either click "Join" in the client to play as a human, run a second instance of your bot, or click "Add Bot" to add a CopperBot opponent.

3. Click "Observe" to watch your bot play! Tweak your bot code and re-run to improve its performance.

**Feeling confident?** Try connecting to the Host's public server during the hacking period to test against other teams' bots!

## Step 4: Compete in the Final Tournament

When the Host announces the hacking period is over, it's time for the knockout tournament.

1. Connect your bot to the Host's public tournament server:
    ```bash
    python hackbot.py --name "TeamName Bot" --server wss://host-codespaces-url.app.github.dev/ws/
    ```
   - Human players can also join by opening the CopperHead client on the tournament server and clicking "Join".

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
