# Narrator

An interactive AI-powered storytelling bot for Discord. Players join a shared text channel, 
take turns describing their actions, and a language model mixes them into a collaborative narrative.

Built with Python, discord.py, and Groq.

## Demo
2 player game, 5 turns, theme = summoners rift, spanish

Original:
<img width="1182" height="347" alt="image" src="https://github.com/user-attachments/assets/07460f38-33f2-426e-bca5-2e3438f484fa" />

Translation:
<img width="1208" height="354" alt="image" src="https://github.com/user-attachments/assets/22837097-fe6e-4c1d-acae-5702d30845b0" />

## Features
- Multi-player support — players join via `/join` before the story begins
- Game saving — resume any game with `/story continue`
- Token usage optimization — the LLM context updates with summaries every 3 turns
- Modular design — LLM provider can be changed without touching game logic
- Generates a readable story after each game

## Architecture
discord_comp -> Discord interface, command parsing and event routing <br />
game -> State machine (idle->waiting for players->(waiting for actions->running)loop) <br />
builder -> Promp construction for the LLM <br />
llm_com -> Groq API calls, summary management and final story prompt <br />
state_comp -> JSON saving and loading <br />

## Setup
1. Clone the repo and install dependencies
```bash
   git clone https://github.com/youruser/discord-story-bot
   cd discord-story-bot
   pip install -r requirements.txt
```
2. Create a `.env` file:
Add<br />
DISCORD_TOKEN = your_discord_bot_token<br />
GROQ_API_KEY= your_grok_api_key<br />

4. Run the bot
```bash
   python bot.py
```
## Usage
`/story new <#players> <#turns> <theme>` | Starts a new game<br />
`/story continue`                        | Resume last saved game<br />
`/join`                                  | Join a game that's waiting for players<br />


## To-Do
- Concurrent games per channel
- Send final story to discord as a message
- Introduce inventory and player character descriptions
- Fine tune prompts
- Change join command (can cause bugs with other bots)
