# How Competitions work in CopperHead

Competitions are managed by the CopperHead server, and includes multiple human and/or bot players. The server settings file determines the basic game rules. An Administrator may control timing and players in the competition by using the CopperHead client in Admin mode, or the competition may run autonomously.

When the server is launched, the `arenas` option determines the number of players in the competition. The competition requires twice that number of players to begin.

## The Lobby

Human or AI players, or a mixture of both, may join the **lobby** as candidate players before the competition begins. Players may join the lobby during active competitions to join the next competition when the current one ends. The `auto_start` setting controls admission and starting:

- **`"always"`** — Players are automatically assigned to match slots as they join. The competition starts when all slots are filled. Ideal for unattended servers.
- **`"admit_only"`** (default) — Players are automatically assigned to match slots, but the Administrator must click Start Competition in the client to begin. After each competition ends, the Administrator must start the next one.
- **`"never"`** — The Administrator manually assigns players to slots (via Admit) and starts the competition. Full manual control.

In `admit_only` and `never` modes, the Administrator can manage the lobby via the admin URL displayed at server startup:

- **Assign slots**: Move players from the lobby into match slots.
- **Kick players**: Remove unwanted players from the lobby.
- **Add bots**: Add CopperBot opponents to the lobby.
- **Start the tournament**: When the Administrator starts the tournament, any empty match slots are auto-filled from the lobby in join order, then with CopperBots if slots remain.

After a tournament ends, players who were waitlisted (in the lobby but not assigned to a slot) remain in the lobby for the next tournament.

## Round 1

In Round 1, players are paired to compete in matches. (Pairing may be controlled by the game Administrator or determined by lobby join order.)

Each match is a series of games played according to the standard CopperHead rules. Winning a game awards one point, and the first player to reach the predefined number of points wins the match and advances to the next round.

## Round 2 and subsequent Rounds

In Round 2, winners from the prior round are paired at random to compete in new matches. This process repeats until only two players remain.

If there are an odd number of players remaining, the player scoring the most points is awarded a "Bye" and automatically advances to the next round without competing in a match. (For the purposes of these calculations, the player with a bye in the current round has scored zero points.) In the case of a tie, the player whose opponent scores the fewest points is awarded the Bye. If there is still a tie, a coin flip determines who receives the Bye.

## Final Round

The final round is a single match between the last two remaining players. The winner of this match is declared the overall competition champion.

This concludes the competition. After a predefined delay, the server resets and begins accepting new players for a new competition.

# Gameplay Details

Players must signal readiness at the beginning of each game. Human players signal readiness by clicking the "Play" button in the client. AI players signal readiness by sending a `ready` action via WebSocket.

Games are governed by the standard CopperHead rules. See [Game Rules](game-rules.md) for full details on game mechanics and scoring.

Players who disconnect during a competition automatically forfeit their matches.




