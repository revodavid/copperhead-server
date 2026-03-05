# How Competitions work in CopperHead

## Before Competition Starts

When the server is launched, the `arenas` option determines the number of players in the competition. The competition will not start until twice that number of players have joined.

Human or AI players, or a mixture of both, may join the server before the competition begins.

No player may join a competition after it begins. Players who disconnect during a competition automatically forfeit their matches.

## Lobby Mode

When `auto_start` is disabled (`false`) in `server-settings.json`, the server uses an admin-controlled lobby system instead of auto-starting the tournament when enough players join.

In lobby mode, players who connect via `/ws/join` enter a **lobby** (waiting room) rather than being placed directly into a match slot. An administrator uses the admin URL (displayed at server startup) to manage the lobby:

- **Assign slots**: Move players from the lobby into match slots.
- **Kick players**: Remove unwanted players from the lobby.
- **Add bots**: Add CopperBot opponents to the lobby.
- **Start the tournament**: When the admin starts the tournament, any empty match slots are auto-filled from the lobby in join order, then with CopperBots if slots remain.

After a tournament ends, players who were waitlisted (in the lobby but not assigned to a slot) remain in the lobby for the next tournament.

## Round 1

In Round 1, players are paired in the order they joined to compete in matches. 

Each match is a series of games played according to the standard CopperHead rules. Winning a game awards one point, and the first player to reach the predefined number of points wins the match and advances to the next round.

## Round 2 and subsequent Rounds

In Round 2, winners from the prior round are paired at random to compete in new matches. If there are an odd number of players remaining, the player scoring the most points is awarded a "Bye" and automatically advances to the next round without competing in a match. (For the purposes of these calculations, the player with a bye in the current round has scored zero points.) In the case of a tie, the player whose opponent scores the fewest points is awarded the Bye. If there is still a tie, a coin flip determines who receives the Bye.

## Final Round

The final round is a single match between the last two remaining players. The winner of this match is declared the overall competition champion.

This concludes the competition. After a predefined delay, the server resets and begins accepting new players for a new competition.






