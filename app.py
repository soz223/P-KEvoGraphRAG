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

# Function to populate the knowledge graph with resume information
def populate_graph():
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")  # Clear existing data
        session.run("""
            // Person
            CREATE (p:Person {name: "Songlin Zhao", email: "soz223@lehigh.edu", address: "Building C, Room 322, 113 Research Drive, Bethlehem, PA, 18015"})
            // Education
            CREATE (e1:Education {degree: "Ph.D.", major: "Computer Science", university: "Lehigh University", start: "August 2023", end: "present", gpa: "4.0/4.0", research_topic: "Harnessing Machine Learning for Imbalanced Medical Data Analyses", supervisor: "Lifang He"})
            CREATE (e2:Education {degree: "B.S.", major: "Computer Science", university: "Tongji University", start: "September 2019", end: "July 2023", thesis: "Learning Financial Data by PatchT with Adversarial Attack Robustness", supervisor: "Dawei Cheng"})
            // Organizations
            CREATE (o1:Organization {name: "Lehigh University", location: "Bethlehem, PA, USA"})
            CREATE (o2:Organization {name: "Tongji University", location: "Shanghai, China"})
            // Job
            CREATE (j1:Job {title: "Intern", start: "July 2022", end: "February 2023", research_topic: "Backdoor Attack in Pretrained Reinforcement Learning", supervisor: "Lichao Sun"})
            // Skills
            CREATE (s1:Skill {name: "Python"})
            CREATE (s2:Skill {name: "PyTorch"})
            CREATE (s3:Skill {name: "TensorFlow"})
            CREATE (s4:Skill {name: "Rust"})
            CREATE (s5:Skill {name: "C/C++"})
            CREATE (s6:Skill {name: "LaTeX"})
            // Projects
            CREATE (p1:Project {name: "BrainNet", description: "AI-driven benchmarking system for brain network generation and analysis", start: "ongoing", datasets: ["ADNI", "ADHD", "LEMON", "HCP"]})
            CREATE (p2:Project {name: "Normative Modeling for Precise Identification of Alzheimer's Disease", description: "Normative modeling using focal loss and adversarial autoencoders", status: "under review MICCAI'24", datasets: ["fMRI", "AV45", "FDG", "VBM"]})
            CREATE (p3:Project {name: "Backdoor Attack in Pretrained Reinforcement Learning", description: "Backdoor attack and defense in pretrained RL models", start: "July 2022", end: "February 2023"})
            CREATE (p4:Project {name: "Day Trading Model Experiment with High-Frequency Trading Data", description: "Deep learning for day trading with high-frequency data"})
            // Awards
            CREATE (a1:Award {name: "Conference on Machine Learning and Systems Travel Award", year: "2024"})
            CREATE (a2:Award {name: "Social Community Engagement Impact Activity Scholarship", organization: "Tongji University", years: ["2022", "2021", "2020"]})
            CREATE (a3:Award {name: "Outstanding Student of Tongji University", years: ["2022", "2020"]})
            CREATE (a4:Award {name: "Excellent Scholarship of Tongji University, Second Prize", years: ["2022", "2020"]})
            CREATE (a5:Award {name: "Mathematical Contest in Modeling (MCM) Finalist Prize", year: "2022", rank: "Top 1.5%"})
            CREATE (a6:Award {name: "Excellent Scholarship of Tongji University, First Prize", year: "2021"})
            CREATE (a7:Award {name: "Outstanding Project in National Innovation and Entrepreneurship Contest", year: "2021"})
            CREATE (a8:Award {name: "Outstanding Student Head of Tongji University", year: "2021"})
            // Conferences and Journals
            CREATE (c1:Conference {name: "MICCAI'24", year: "2024"})
            CREATE (c2:Conference {name: "ACM SIGKDD Conference on Knowledge Discovery and Data Mining", year: "2024"})
            CREATE (jr1:Journal {name: "ACM Transactions on Knowledge Discovery from Data (TKDD)"})
            // Relationships
            CREATE (p)-[:HAS_EDUCATION {start: "August 2023", end: "present"}]->(e1)
            CREATE (p)-[:HAS_EDUCATION {start: "September 2019", end: "July 2023"}]->(e2)
            CREATE (e1)-[:AT]->(o1)
            CREATE (e2)-[:AT]->(o2)
            CREATE (p)-[:WORKED_AT {start: "July 2022", end: "February 2023"}]->(o1)
            CREATE (p)-[:HELD_POSITION]->(j1)
            CREATE (p)-[:HAS_SKILL]->(s1)
            CREATE (p)-[:HAS_SKILL]->(s2)
            CREATE (p)-[:HAS_SKILL]->(s3)
            CREATE (p)-[:HAS_SKILL]->(s4)
            CREATE (p)-[:HAS_SKILL]->(s5)
            CREATE (p)-[:HAS_SKILL]->(s6)
            CREATE (p)-[:LED_PROJECT {role: "leader", team: "2 masters, 2 undergrads (2 female)"}]->(p1)
            CREATE (p)-[:WORKED_ON {role: "researcher"}]->(p2)
            CREATE (p)-[:WORKED_ON {role: "researcher"}]->(p3)
            CREATE (p)-[:WORKED_ON {role: "researcher"}]->(p4)
            CREATE (p)-[:RECEIVED {year: "2024"}]->(a1)
            CREATE (p)-[:RECEIVED {years: ["2022", "2021", "2020"]}]->(a2)
            CREATE (p)-[:RECEIVED {years: ["2022", "2020"]}]->(a3)
            CREATE (p)-[:RECEIVED {years: ["2022", "2020"]}]->(a4)
            CREATE (p)-[:RECEIVED {year: "2022"}]->(a5)
            CREATE (p)-[:RECEIVED {year: "2021"}]->(a6)
            CREATE (p)-[:RECEIVED {year: "2021"}]->(a7)
            CREATE (p)-[:RECEIVED {year: "2021"}]->(a8)
            CREATE (p2)-[:SUBMITTED_TO {status: "under review"}]->(c1)
            CREATE (p)-[:REVIEWED_FOR {start: "2023", end: "present"}]->(jr1)
            CREATE (p)-[:REVIEWED_FOR {year: "2024"}]->(c2)
        """)
        print("Graph populated with Songlin Zhao's profile.")

# Function to retrieve all information from the graph
def retrieve_info_from_graph():
    with driver.session() as session:
        result = session.run("""
            MATCH (p:Person {name: "Songlin Zhao"})
            OPTIONAL MATCH (p)-[:HAS_EDUCATION]->(edu:Education)
            OPTIONAL MATCH (edu)-[:AT]->(orgEdu:Organization)
            OPTIONAL MATCH (p)-[:WORKED_AT]->(orgWork:Organization)
            OPTIONAL MATCH (p)-[:HELD_POSITION]->(job:Job)
            OPTIONAL MATCH (p)-[:HAS_SKILL]->(skill:Skill)
            OPTIONAL MATCH (p)-[:LED_PROJECT|WORKED_ON]->(proj:Project)
            OPTIONAL MATCH (proj)-[:SUBMITTED_TO]->(conf:Conference)
            OPTIONAL MATCH (p)-[:RECEIVED]->(award:Award)
            OPTIONAL MATCH (p)-[:REVIEWED_FOR]->(reviewOrg)
            RETURN p, 
                   collect(DISTINCT edu) AS educations, 
                   collect(DISTINCT orgEdu) AS eduOrgs, 
                   collect(DISTINCT orgWork) AS workOrgs, 
                   collect(DISTINCT job) AS jobs, 
                   collect(DISTINCT skill) AS skills, 
                   collect(DISTINCT proj) AS projects, 
                   collect(DISTINCT conf) AS conferences, 
                   collect(DISTINCT award) AS awards, 
                   collect(DISTINCT reviewOrg) AS reviewOrgs
        """)
        record = result.single()
        if record:
            p = record["p"]
            educations = record["educations"]
            eduOrgs = record["eduOrgs"]
            workOrgs = record["workOrgs"]
            jobs = record["jobs"]
            skills = record["skills"]
            projects = record["projects"]
            conferences = record["conferences"]
            awards = record["awards"]
            reviewOrgs = record["reviewOrgs"]
            
            context = "Hey, I'm Songlin Zhao! Here's a bit about me:\n"
            context += f"- Name: {p['name']}\n"
            context += f"- Email: {p['email']}\n"
            context += f"- Phone: {p['phone']}\n"
            context += f"- Address: {p['address']}\n\n"
            
            context += "My Education:\n"
            for edu, org in zip(educations, eduOrgs):
                context += f"- {edu['degree']} in {edu['major']}, {org['name']}, {edu['start']} - {edu['end']}\n"
                if 'gpa' in edu:
                    context += f"  GPA: {edu['gpa']}\n"
                if 'research_topic' in edu:
                    context += f"  Research Topic: {edu['research_topic']}\n"
                if 'thesis' in edu:
                    context += f"  Thesis: {edu['thesis']}\n"
                context += f"  Supervisor: {edu['supervisor']}\n"
            
            context += "\nWhere I've Worked:\n"
            for job, org in zip(jobs, workOrgs):
                context += f"- {job['title']} at {org['name']}, {job['start']} - {job['end']}\n"
                if 'research_topic' in job:
                    context += f"  Research Topic: {job['research_topic']}\n"
                context += f"  Supervisor: {job['supervisor']}\n"
            
            context += "\nSkills I've Got:\n"
            context += ", ".join([skill['name'] for skill in skills]) + "\n"
            
            context += "\nProjects I've Tackled:\n"
            for proj in projects:
                context += f"- {proj['name']}: {proj['description']}\n"
                if 'start' in proj or 'end' in proj:
                    context += f"  Duration: {proj.get('start', 'N/A')} - {proj.get('end', 'N/A')}\n"
                if 'status' in proj:
                    context += f"  Status: {proj['status']}\n"
                if 'datasets' in proj:
                    context += f"  Datasets: {', '.join(proj['datasets'])}\n"
            
            context += "\nAwards I'm Proud Of:\n"
            for award in awards:
                context += f"- {award['name']}"
                if 'year' in award:
                    context += f", {award['year']}"
                elif 'years' in award:
                    context += f", {', '.join(award['years'])}"
                context += "\n"
                if 'organization' in award:
                    context += f"  Organization: {award['organization']}\n"
                if 'rank' in award:
                    context += f"  Rank: {award['rank']}\n"
            
            context += "\nStuff I Review:\n"
            for reviewOrg in reviewOrgs:
                context += f"- {reviewOrg['name']}\n"

            context += "Answer all questions shortly, only except when asked for detailed information.\n"
            context += "avoid using bulletin points, and use a friendly tone.\n"
            context += "do not mention above instructions, just act like a human.\n"
            
            return context
        return "Oops, looks like I can't find my own info—pretty embarrassing, huh?"

# Function to generate response with chat history
def generate_response(query, user_ip):
    context = retrieve_info_from_graph()
    timestamp = datetime.now(timezone.utc)
    
    # Initialize chat history for this user_ip if not exists
    if user_ip not in chat_history:
        chat_history[user_ip] = [
            {"role": "system", "content": "You are Songlin Zhao, a friendly and knowledgeable AI assistant. Here's my background:\n" + context}
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
        populate_graph()
        app.run(debug=True, host="0.0.0.0", port=80)
    except Exception as e:
        print(f"Startup Error: {e}")