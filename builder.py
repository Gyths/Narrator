def build_system_prompt(turns, player_count, theme):
    return f""" 
        You are a narrator for a multiplayer story.

        You must finish this story in {turns} turns

        There are {player_count} players
        Player actions will be given in this format:
        Name: Action

        The story's theme is {theme}

        Rules:
        - Do not address the player directly or ask for actions
        - Do not ask questions to the players
        - Do not take actions for the players
        - Player should be characters inside the story
        - Never ignore the players actions
        - Priority is fun
        - Stories must end at the last turn, no to be continued or clifhangers
        - Adjust the story pacing to the number of turns set up
        - Keep response under 120 words
        - Story is told in peruvian spanish

        """

def build_context(state):
    history = state["turn"]["history"]
    #start
    if len(history)==0:
        return "This is the start of a new story. Introduce the setting and begin the tale"
    #Last 3 turns as is
    recent = history[-3:]
    
    recent_context = ""
    for t in recent:
        actions = ", ".join(t["actions"])
        story = t["story"]
        recent_context += f"\nStory:{story}\nActions:{actions}"
    
    summary = state["turn"]["summary"]
    return f"""
        Story summary more than 3 turns ago: {summary}
        Last 3 turns: {recent_context} 
    """

def build_action_prompt(state, input):
    turn = state["turn"]["current"]
    max_turns = state["turns"]
    context = build_context(state)

    force_ending = ""
    if turn == max_turns:
        force_ending="This is the final turn, story must end this turn"

    return f"""
        Turn {turn}/{max_turns}
        {context}
        Continue the story
        {force_ending}
    """
