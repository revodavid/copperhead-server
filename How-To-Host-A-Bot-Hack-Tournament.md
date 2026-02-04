# Hosting a CopperHead Bot Hack Tournament

Looking for a fun way to hang out with your tech friends? Host a CopperHead Bot Hack Tournament! CopperHead is a head-to-head Snake game tournament server that supports AI bots, making it perfect for competitive programming events.

A CopperHead Bot Hack Tournament is simple: after an hour or two hacking together bots to play the Snake game, the winner is the team whose bot wins out against all other bots (and maybe even humans!) in a knockout tournament hosted on a CopperHead server. 

**You will need**:
- One person (the Host) to run the event (the host can participate as well)
- 4 participants with Github accounts (more is better!)
  * GitHub accounts are free and include [GitHub Copilot](https://github.com/features/copilot) and [GitHub Codespaces](https://github.com/features/codespaces) access, both of which will be very useful during this event.
- One laptop per team with internet access 
  * Any laptop will do. All code runs in GitHub Codespaces, so no local installation or cloud account is needed.
- [optional] A big screen for watching the final tournament

## Step 1: Gather your crew

A bot-hack tournament needs at least 4 teams, but more is better! Aim for 8-30 participants, formed into teams of 1 or 2. Participants can have any level of programming experience, from beginner to expert. Non-coders can join in the fun as playtesters and human competitors in the final tournament.

Ideally, gather everyone together in a room with good WiFi and power outlets, and space to spread out and/or form teams. Each participant will need a laptop to code on, and a web browser to connect to the CopperHead client.

Divide your crew into teams of one or two people -- you will need at least 4 teams. Each team should choose a unique team name.

## Step 2: Define the game rules and prepare the server

The CopperHead server provides many configurable settings for the game rules: number of points to win, grid size, game speed, fruit types and frequencies, buffs, and more. Changing the rules changes the best strategies to win, making every tournament unique!

As host, fork the [copperhead-server](https://github.com/revodavid/copperhead-server) repository to your own GitHub account. Edit the [`server-settings.json`](server-settings.json) file to define the rules for your game. (Leave the `arenas` setting at 1 for now - you will increase it to accommodate all competing teams just before the final tournament.)

Follow the instructions in the [CopperHead Server README](https://github.com/revodavid/copperhead-server) to launch the server in GitHub Codespaces. Launch the CopperHead client as instructed to launch the game and show it on the big screen if available. This server will serve as a public arena for all teams to connect to during the hacking period and the final tournament.

Share your modified `server-settings.json` file and the server URL for your game with all participants so they can code their bots to the correct game rules.

## Step 2: Let the bot building begin!

Set a time limit for bot development - 1 hour is sufficient for AI-supported coding, longer for manual coding or more sophisticated strategy development. Ring a bell or use a timer to signal the start and end of the hacking period. When the hacking period is over, the final competition begins!

Each team should begin by forking the [copperhead-server](https://github.com/revodavid/copperhead-server) repository to their own GitHub account, and updating the `server-settings.json` file to match the host's game rules. Launch a server in GitHub Codespaces for the team to use in development. (TIP: you can restart the server at any time by modifying and saving the `server-settings.json` file.)

Teams should then create their own `hackbot.py` file to build their bot -- copying the default `copperbot.py` file from the repository is a great place to start. (You can find other bots to inspire your own in the `bot-library` directory.) Make sure the bot assigns itself a unique name matching the team name.

### How do I write a bot?

See [Building-Your-Own-Bot.md](Building-Your-Own-Bot.md) in the copperhead-server repository for detailed instructions on building a bot. The [Game Rules](game-rules.md) and [Competition Logic](competition-logic.md) documents are also useful references.

Using a coding agent like [GitHub Copilot](https://github.com/features/copilot) speeds up the process of making a competitive bot in the time allowed:

* Anyone can use GitHub Copilot straight from the GitHub web interface - no code editor required!
* Beginner programmers can use GitHub Copilot CLI to generate code from natural language prompts, even without coding experience.
* Experienced programmers can use GitHub Copilot in their favorite IDE to speed up bot development.

You can use any AI support you like! See how your favorite coding assistant fares in the competition versus bots made with other tools.

If you don't want to code at all, you can still join in the fun by suggesting and testing bot strategies as a human opponent during the hacking period.

### How do I test my bot?

Each team should launch their own instance of the game server in GitHub Codespaces to test their bot during the hacking period. Also launch the client on your team server with the "Play Now" link shown in Codespaces.
To test your bot:

1. Launch your bot on the team server:
    ```bash
    python hackbot.py --name "TeamName Bot" --server wss://github-codespaces-url.app.github.io/ws/
    ```
   * You can find the server URL in the Codespaces terminal output, and at the bottom of the client lobby screen.

   * You can skip the --name argument if your bot assigns itself a name in code.

2. In the game client, either add a human player by clicking "Join", launch a second bot by running another instance of your bot code, or add a CopperBot opponent by clicking "Add Bot" in the client.

3. Click the "Observe" button to watch your bot playing the game! Adjust your bot code as needed to improve its performance.

Feeling confident? Try testing your bot against other teams' bots by connecting to the host's public server during the hacking period!

## Step 3: The Final Tournament

When the hacking period ends, it's time for the final tournament! At this point, humans may join the tournament as a team, if you like.

1. As host, increase the `arenas` setting in your server's `server-settings.json` file to half the number of participating teams (rounded up). For example, if you have 7 teams, set `arenas` to 4 to accommodate all teams in Round 1.

2. Each team should connect their bot to the host's public server by running their bot code with the host's server URL:
    ```bash
    python hackbot.py --name "TeamName Bot" --server wss://host-codespaces-url.app.github.dev/ws/
    ```
   * Human players may also join by launching the Copperhead client on the tournament server and clicking "Join".
 
   * If still have an odd number of teams, you will need to add a bot opponent to begin the tournament. Click "Add Bot" in the client lobby to add a Level 1 CopperBot opponent.

3. When all teams have joined, the tournament will begin automatically. Watch the action on the big screen as teams compete in knockout rounds. The Host controls the action on the Observer screen, switching between active games and providing commentary.

4. The winning team is the human or bot that wins the final match! Celebrate their victory -- oversized champagne bottles optional.

## Step 4: Save your bots!

Save your bots to your forked github repository. You can do this from the Source Control panel in Codespaces, or by committing and pushing changes via the terminal:
    git add .
    git commit -m "My hack tournament bot"
    git push

If you're on a free GitHub account, you should probably also delete your Codespace to avoid using up your free hours. You can do that at https://github.com/codespaces.

If you made a really awesome bot, consider submitting a pull request to add it to the [bot-library](bot-library) directory so others can use it in future tournaments!

## Most importantly, have fun!

We hope you had a great time hosting or participating in a CopperHead Bot Hack Tournament! We're always excited to hear about how people are using CopperHead for fun and learning. If you have feedback, suggestions, or stories to share, please open an issue in the [copperhead-server](https://github.com/revodavid/copperhead-server) repository.






