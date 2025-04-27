from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
from neo4j import GraphDatabase
from datetime import datetime, timezone
import os
import socket
import json
from openai import OpenAI

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# DeepSeek API setup using OpenAI SDK with environment variable
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not API_KEY:
    raise ValueError("DEEPSEEK_API_KEY environment variable not set")
client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# Neo4j setup
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")  # Default if not set
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")  # Replace or set via env
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Log file setup
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "user_history.json")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# In-memory chat history (user_ip -> list of messages)
chat_history = {}

# Function to log user interaction
def log_interaction(user_ip, timestamp, user_request, response):
    log_entry = {
        "timestamp": timestamp.isoformat(),
        "user_ip": user_ip,
        "hostname": socket.gethostname(),
        "request": user_request,
        "response": response,
        "server_time": datetime.now(timezone.utc).isoformat()
    }
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        json.dump(log_entry, f, ensure_ascii=False)
        f.write('\n')

# Function to retrieve information from the stored Neo4j graph
def retrieve_info_from_graph():
    with driver.session() as session:
        # Query all Concept nodes and their relationships
        result = session.run("""
            MATCH (c:Concept)-[r:RELATED_TO]->(related:Concept)
            RETURN c, collect(related) AS related_concepts
        """)
        
        context = "Here's what I know from my knowledge graph:\n"
        concepts_found = False
        
        for record in result:
            concepts_found = True
            concept = record["c"]["name"]
            related = [rel["name"] for rel in record["related_concepts"]]
            
            context += f"- Concept: {concept}\n"
            if related:
                context += f"  Related to: {', '.join(related)}\n"
            else:
                context += "  No related concepts found.\n"
        
        if not concepts_found:
            return "Oops, looks like my knowledge graph is empty—nothing to share yet!"
        
        return context

# Function to generate response with chat history
def generate_response(query, user_ip):
    context = retrieve_info_from_graph()
    timestamp = datetime.now(timezone.utc)
    
    # Initialize chat history for this user_ip if not exists
    if user_ip not in chat_history:
        chat_history[user_ip] = [
            {"role": "system", "content": "You are a friendly and knowledgeable AI assistant. Here's my background:\n" + context}
        ]
    
    # Append the new user query to the history
    chat_history[user_ip].append({"role": "user", "content": query})
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=chat_history[user_ip],  # Send the full conversation history
            max_tokens=512,
            temperature=0.9,
            top_p=0.95,
            stream=False
        )
        
        generated_response = response.choices[0].message.content
        # Append the AI's response to the history
        chat_history[user_ip].append({"role": "assistant", "content": generated_response})
        
        # Limit history size to prevent excessive memory use
        if len(chat_history[user_ip]) > 10:  # Keep last 10 messages (5 turns)
            chat_history[user_ip] = chat_history[user_ip][-10:]
        
        log_interaction(user_ip, timestamp, query, generated_response)
        return generated_response
        
    except Exception as e:
        print(f"API Error: {e}")
        error_response = "Hey, something went wonky with my brain—can’t answer that right now. Maybe try again?"
        log_interaction(user_ip, timestamp, query, error_response)
        return error_response

# Flask routes
@app.route('/', methods=['GET', 'POST'])
def home():
    user_ip = request.remote_addr
    if request.method == 'POST':
        question = request.form.get('question')
        if not question:
            error_response = "Please enter a question"
            log_interaction(user_ip, datetime.now(timezone.utc), "", error_response)
            return jsonify({"response": error_response}), 400
        response = generate_response(question, user_ip)
        return jsonify({'response': response})
    return render_template('index.html')

if __name__ == '__main__':
    try:
        # No need to populate_graph() anymore—use existing Neo4j data
        app.run(debug=True, host="0.0.0.0", port=80)
    except Exception as e:
        print(f"Startup Error: {e}")