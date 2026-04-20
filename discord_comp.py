import discord
import os
from dotenv import load_dotenv

from game import Game

load_dotenv()

# ── Intents ──────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ── Game session ───────────────────────────────────
game: Game | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────
def parse_story_command(content: str):
    """
    Parse:  /story new <players> <turns> <theme>
            /story continue
    Returns a dict or None if malformed.
    """
    parts = content.split()
    if len(parts) < 2:
        return None

    mode = parts[1].lower()

    if mode == "continue":
        return {"mode": "continue"}

    if mode == "new":
        if len(parts) < 5:
            return None
        try:
            return {
                "mode": "new",
                "player_count": int(parts[2]),
                "turns": int(parts[3]),
                "theme": " ".join(parts[4:]),
            }
        except ValueError:
            return None

    return None


async def send(channel, text: str):
    #Send a message, splitt if it exceeds Discord's 2000-char limit.
    for i in range(0, len(text), 2000):
        await channel.send(text[i : i + 2000])


# ── Events ───────────────────────────────────────────────────────────────────
@client.event
async def on_ready():
    print("El narrador esta listo")


@client.event
async def on_message(message: discord.Message):
    global game

    # Ignore own messages
    if message.author == client.user:
        return

    content = message.content.strip()
    channel = message.channel

    # ── /story ────────────────────────────────────────────────────────────────
    if content.startswith("/story"):
        if game is not None:
            await send(channel, "Ya hay una historia activa. Espera a que termine.")
            return

        args = parse_story_command(content)
        if args is None:
            await send(
                channel,
                "Los comandos aceptados son: `/story new <jugadores> <turnos> <tema>`  o  `/story continue`",
            )
            return

        game = Game(channel, client, send)

        if args["mode"] == "new":
            await game.start_new(
                host_id=str(message.author.id),
                host_name=message.author.display_name,
                player_count=args["player_count"],
                turns=args["turns"],
                theme=args["theme"],
            )
        else:
            await game.start_continue()

        return

    # ── /join ─────────────────────────────────────────────────────────────────
    if content.startswith("/join"):
        if game is None:
            await send(channel, "No te puedes unir a una historia que no existe.")
            return
        await game.handle_join(
            player_id=str(message.author.id),
            player_name=message.author.display_name,
            channel=channel,
        )
        return

    # ── In-game actions ───────────────────────────────────────────────────────
    if game is not None and game.is_waiting_for_actions():
        await game.handle_action(
            player_id=str(message.author.id),
            player_name=message.author.display_name,
            content=content,
            channel=channel,
        )
        return


client.run(os.getenv("DISCORD_TOKEN"))