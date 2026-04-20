from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("API_KEY"))

def call_llm(prompt,system_prompt=""):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1200
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error: {e}"

def update_summary(state):
    history = state["turn"]["history"]
    prompt = f""" 
        Summarize this story so far in no more than 5 sentences keeping as much detail as posible
        do not change the language, keep it as spanish
        {history}
    """
    summary = call_llm(prompt,"You are a summarization assistant")
    state["turn"]["summary"] = summary

def generate_txt(state):
    history = state["turn"]["history"]
    prompt = f""" 
        Make this into a novel format for archiving purposes
        it should read as a story not just dialogue, include the players as characters in it
        do not add unnecesary details
        adjust the length depending on the number of turns
        do not change the language, keep it as spanish
        do not change the players name
        give the story a name before starting
        {history}
    """
    return call_llm(prompt, "You are an experienced writer")