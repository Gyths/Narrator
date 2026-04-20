import json

def load_state():
    with open("state.json","r") as f:
        return json.load(f)
    
def save_state(state):
    with open("state.json","w") as f:
        json.dump(state,f,indent=2)