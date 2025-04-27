import re
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')

from nltk.tokenize import sent_tokenize

# Read the text file
with open('input_text.txt', 'r') as file:
    text = file.read()

# Clean the text
def clean_text(text):
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    return text.strip()

cleaned_text = clean_text(text)

# Tokenize into sentences
sentences = sent_tokenize(cleaned_text)

# Split the text into chunks

from langchain.text_splitter import CharacterTextSplitter

text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
chunks = text_splitter.split_text(cleaned_text)



# Extract entities from the text
from transformers import pipeline

ner_pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")

def extract_entities(chunk):
    entities = ner_pipeline(chunk)
    return [entity['word'] for entity in entities if entity['entity'] in ['B-PER', 'B-ORG', 'B-LOC']]

concepts = [extract_entities(chunk) for chunk in chunks]



# Extract embeddings for the chunks
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(chunks)  # Not used directly here, but useful for future enhancements


relationships = []
for chunk_concepts in concepts:
    for i in range(len(chunk_concepts)):
        for j in range(i + 1, len(chunk_concepts)):
            relationships.append((chunk_concepts[i], chunk_concepts[j]))



print(relationships)