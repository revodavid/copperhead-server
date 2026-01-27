# CopperHead Game Rules

A game of CopperHead is played between two players on a rectangular grid. Each player controls a snake that moves around the grid, trying to eat food items to grow longer while avoiding collisions with walls, themselves, and the other player's snake.

The first player to collide with the wall or another player (unless protected by a buff) loses the game and the other player is awarded one point. 

If both players collide simultaneously, the game ends in a draw and no points are awarded. Exception: if players collide head-to-head and only one player changed direction in the last move, that player loses and the other player is awarded the point.

The size of the grid is configurable via server settings.

## Movement

Each player's snake moves automatically in the current direction at a fixed speed. Players can change the direction of their snake using control inputs (e.g., arrow keys or WASD keys).

Snakes cannot reverse direction (e.g., if moving right, they cannot move left). Players must make successive left or right turns to change direction.

## Fruit Bonuses

During gameplay, various fruit items may appear on the game grid. These fruits provide different bonuses when collected by a player's snake. The available fruit bonuses are as follows:

- 🍎 Apple: increases player snake length by one
- 🍊 Orange: no effect
- 🍋 Lemon: no effect
- 🍇 Grapes: increases player snake length by one. decreases opponent's snake length by one if greater than one.
- 🍓 Strawberry: no effect
- 🍌 Banana: no effect
- 🍑 Peach: no effect
- 🍒 Cherry: no effect
- 🍉 Watermelon: no effect
- 🥝 Kiwi: no effect

The server controls which food items which appear, and at what frequency, and how long they remain on the grid.

By default, exactly one one apple may appear at a time, and no other fruits appear.

## Buffs

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


