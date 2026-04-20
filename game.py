"""
game.py — Game loop for interactive story bot.

States
------
  idle            → no game running
  waiting_players → host created game, waiting for /join
  waiting_actions → story segment sent, collecting player actions
  running         → processing LLM / summary ("thinking")
  finished        → story ended

The Game object is created fresh for each session.
"""

import asyncio
from typing import Callable, Awaitable

from state_comp import load_state, save_state
from builder import build_action_prompt, build_system_prompt
from llm_com import call_llm, update_summary, generate_txt


# Type alias for the send helper injected from bot.py
SendFn = Callable[[object, str], Awaitable[None]]


class Game:
    def __init__(self, channel, client, send_fn: SendFn):
        self.channel = channel          # default channel
        self.client = client
        self._send = send_fn

        self._state_name = "idle"
        self.state: dict = {}           # JSON state
        self.system_prompt: str = ""

        # Pending actions for the current turn: {player_id: (name, action)}
        self._pending: dict[str, tuple[str, str]] = {}
        self._current_story: str = ""

    # ── Public state queries ─────────────────────────────────────────────────

    def is_waiting_for_actions(self) -> bool:
        return self._state_name == "waiting_actions"

    def is_waiting_for_players(self) -> bool:
        return self._state_name == "waiting_players"

    # ── Session startup ──────────────────────────────────────────────────────

    async def start_new(
        self,
        host_id: str,
        host_name: str,
        player_count: int,
        turns: int,
        theme: str,
    ):
        #Initialize a new game state and wait for players to /join.
        self.state = _make_state(
            host_id=host_id,
            host_name=host_name,
            player_count=player_count,
            turns=turns,
            theme=theme,
        )
        save_state(self.state)

        self.system_prompt = build_system_prompt(
            self.state["turns"],
            self.state["player_count"],
            self.state["theme"],
        )

        self._state_name = "waiting_players"

        missing = player_count - 1  # host already joined
        if missing <= 0:
            # Single-player game — start immediately
            await self._begin_turn_loop()
        else:
            await self._send(
                self.channel,
                f"🎲 **Nueva historia** | Temática: *{theme}* | {turns} turnos | "
                f"{player_count} jugadores\n"
                f"Esperando {missing} jugador(es) más. Usa `/join` para unirte.",
            )

    async def start_continue(self):
        """Load an existing state.json and resume."""
        try:
            self.state = load_state()
        except FileNotFoundError:
            await self._send(self.channel, "No hay partida guardada para continuar.")
            return

        self.system_prompt = build_system_prompt(
            self.state["turns"],
            self.state["player_count"],
            self.state["theme"],
        )

        await self._send(
            self.channel,
            f"▶️ Reanudando partida en el turno {self.state['turn']['current']}.",
        )
        await self._begin_turn_loop()

    # ── Player join ──────────────────────────────────────────────────────────

    async def handle_join(self, player_id: str, player_name: str, channel):
        if self._state_name != "waiting_players":
            await self._send(channel, "La historia no está aceptando nuevos jugadores.")
            return

        players = self.state["players"]

        if player_id in players:
            await self._send(channel, f"{player_name}, ya estás en la historia.")
            return

        expected = self.state["player_count"]
        if len(players) >= expected:
            await self._send(channel, "no hay espacio para otro personaje.")
            return

        # Register player with the next available slot id
        pid = f"p{len(players) + 1}"
        players[pid] = {"id": player_id, "name": player_name, "description": ""}
        save_state(self.state)

        await self._send(channel, f"**{player_name}** se unió.")

        if len(players) >= expected:
            await self._begin_turn_loop()

    # ── Action collection ────────────────────────────────────────────────────

    async def handle_action(
        self, player_id: str, player_name: str, content: str, channel
    ):
        #Called by bot.py for every message while state is waiting_actions.
        players = self.state["players"]

        # Check this user is actually a player
        pid = _find_pid(players, player_id)
        if pid is None:
            return  # not a player, ignore silently

        if pid in self._pending:
            await self._send(channel, f"{player_name}, ya enviaste tu acción este turno.")
            return

        self._pending[pid] = (player_name, content)

        remaining = len(players) - len(self._pending)
        if remaining > 0:
            print(f"⏳ Acción recibida ({len(self._pending)}/{len(players)}).")
        else:
            # All actions collected — advance the turn
            await self._advance_turn()

    # ── Internal turn loop ───────────────────────────────────────────────────

    async def _begin_turn_loop(self):
        #Send the first story prompt and start collecting actions.
        self._state_name = "running"
        await self._send(
            self.channel,
            f"La historia comienza | "
            f"{self.state['player_count']} jugador(es) | {self.state['turns']} turnos.",
        )
        await self._run_turn()

    async def _run_turn(self):
        #Build prompt, call LLM, broadcast response, wait for actions.
        turn_num = self.state["turn"]["current"]

        if turn_num > self.state["turns"]:
            await self._finish()
            return

        await self._send(self.channel, f"Turno {turn_num}")

        # Build inputs list from turn's pending actions (empty on turn 1)
        inputs = list(self._pending.values()) if self._pending else []
        self._pending = {}

        action_prompt = build_action_prompt(self.state, inputs)

        # Run the blocking LLM call in a thread to avoid blocking the event loop
        response = await asyncio.get_event_loop().run_in_executor(
            None, call_llm, action_prompt, self.system_prompt
        )
        self._current_story = response
        await self._send(self.channel, response)

        

        # Save last turn's data (inputs already collected before this call)
        if inputs:
            self.state["turn"]["history"].append({
                "turn": turn_num - 1,
                "story": response,
                "actions": [f"{name}: {action}" for name, action in inputs],
            })
            save_state(self.state)

        self._state_name = "waiting_actions"

    async def _advance_turn(self):
        #Called once all players have submitted their actions.
        self._state_name = "running"

        inputs = list(self._pending.values())
        # Save actions into history
        turn_num = self.state["turn"]["current"]
        
        self.state["turn"]["history"].append({
            "turn": turn_num,
            "story": self._current_story,       
            "actions": [f"{name}: {action}" for name, action in inputs],
        })
        self._current_story = ""
        
        # Periodic summary every 3 turns
        if turn_num % 3 == 0:
            await asyncio.get_event_loop().run_in_executor(
                None, update_summary, self.state
            )
            
        #Next turn
        self.state["turn"]["current"] += 1
        save_state(self.state)
        
        await self._run_turn()

    async def _finish(self):
        """End the game, generate the final story file, reset global session."""
        self._state_name = "finished"

        tale = await asyncio.get_event_loop().run_in_executor(
            None, generate_txt, self.state
        )

        with open("story.txt", "w") as f:
            f.write(tale)

        await self._send(self.channel, "Historia guardada.")

        # Reset global session in bot.py by importing and nullifying
        import discord_comp
        discord_comp.game = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_state(
    host_id: str,
    host_name: str,
    player_count: int,
    turns: int,
    theme: str,
) -> dict:
    return {
        "players": {
            "p1": {"id": host_id, "name": host_name, "description": ""}
        },
        "turn": {
            "current": 1,
            "history": [],
            "summary": "",
        },
        "turns": turns,
        "player_count": player_count,
        "theme": theme,
    }


def _find_pid(players: dict, discord_id: str) -> str | None:
    #Slot key (e.g. 'p2') for a given Discord user id, or None.
    for pid, data in players.items():
        if data["id"] == discord_id:
            return pid
    return None