# CopperHead Game Rules

A game of CopperHead is played between two players on a rectangular grid. Each player controls a snake that moves around the grid, trying to eat food items to grow longer while avoiding collisions with walls, themselves, and the other player's snake.

The first player to collide with the wall or another player (unless protected by a buff) loses the game and the other player is awarded one point. 

If both players crash simultaneously, the player with the longest snake wins the point. If both players have snakes of equal length, the player who changed direction most recently loses and their opponent wins the point. Otherwise, the game ends in a draw and no points are awarded.

Many game parameters are configurable via [server settings](server-settings.json), including:
- the size of the game grid,
- the types, frequencies and lifetime of food items that appear, and
- the buffs that are available. 

## Movement

Each player's snake moves automatically in the current direction at a fixed speed. Players can change the direction of their snake using control inputs (e.g., arrow keys or WASD keys).

Snakes cannot reverse direction (e.g., if moving right, they cannot move left). Players must make successive left or right turns to change direction.

## Fruit Bonuses

During gameplay, various fruit items may appear on the game grid. These fruits provide different bonuses when collected by a player's snake. The available fruit bonuses are as follows:

- 🍎 Apple: increases player snake length by one
- 🍊 Orange: not yet implemented 
- 🍋 Lemon: not yet implemented
- 🍇 Grapes: increases player snake length by one. decreases opponent's snake length by one if greater than one.
- 🍓 Strawberry: not yet implemented
- 🍌 Banana: not yet implemented
- 🍑 Peach: not yet implemented
- 🍒 Cherry: not yet implemented
- 🍉 Watermelon: not yet implemented
- 🥝 Kiwi: not yet implemented

By default, exactly one fruit may appear at a time. Apples appear 90% of the time (propensity 9) and grapes appear 10% of the time (propensity 1). Grapes expire after 20 ticks if not collected.

## Buffs

NOTE: Buffs are not yet implemented. The following is the intended design for buffs, which may be subject to change.

Each player snake posseses exactly one buff at a time. Buffs provide temporary advantages or abilities to the player snake. Collecting fruit may change the active buff. The available buffs are as follows:

- 👀 Default: the snake has no special abilities. This buff is applied at game start and when any buff is removed.
- ⚡ Speed Boost: the snake moves at double speed.
- 🛡️ Shield: the snake will automatically turn if it hits the wall, and also removes this buff.
- 🔄 Inversion: the snake's controls are inverted
- 🍀 Lucky: appearing fruit will appear within 5 tiles of the player's head with 50% probability.
- 🐢 Slow: the opponent's snake moves at half speed.
- 👻 Ghost: instead of colliding with walls, the snake passes through walls and appears on the opposite side. 
- ? Question Mark: a random buff is applied when the player collects this fruit.

Only the Default buff is enabled by default. Other buffs may be enabled by enabling the corresponding fruit via server settings.
