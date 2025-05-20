# app.py

from flask import Flask, render_template, request
from dotenv import load_dotenv
import os

# LangChain & Pinecone
from langchain_openai import OpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_pinecone import PineconeVectorStore
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.embeddings import HuggingFaceEmbeddings

# Custom code
from src.prompt import system_prompt
from src.helper import download_hugging_face_embeddings

# Flask app initialization
app = Flask(__name__)
load_dotenv()

# Load API keys
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Load the embedding model (same one used during indexing)
embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Load Pinecone vector store from existing index
index_name = "ecohusk"
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings_model,
)

# Set up retrieval chain
retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 3})
llm = OpenAI(temperature=0.4, max_tokens=2000)

# Load the system prompt dynamically
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])

# Build the full RAG chain
question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

# Flask Routes
@app.route("/")
def index():
    return render_template('chat.html')




from langdetect import detect
import re

@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"].strip()
    print(f"User input: {msg}")

    # Convert to lowercase for easier matching
    msg_lower = msg.lower()

    # Clean non-alphanumeric characters for detection
    cleaned_msg = re.sub(r"[^\w\s]", "", msg_lower)

    # Common greetings and expressions
    greetings = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]
    how_are_you = ["how are you", "how are you doing", "how are you today", "how's it going"]
    thanks = ["thank you", "thanks", "thx", "thank u"]
    farewells = ["bye", "goodbye", "see you", "farewell", "talk to you later"]

    # Manual check for common English expressions
    if any(greet in cleaned_msg for greet in greetings):
        return "Hello! I am EcoHusk Chatbot. What do you want to know about the EcoHusk project?"

    if any(phrase in cleaned_msg for phrase in how_are_you):
        return "I am a Chatbot. I don't have feelings, but I'm here to help! What would you like to know about EcoHusk?"

    if any(word in cleaned_msg for word in farewells):
        return "You're welcome! Feel free to return if you have more questions. Goodbye!"

    if any(word in cleaned_msg for word in thanks):
        return "You're most welcome! Let me know if you have more questions about EcoHusk."

    # Language detection fallback for other languages
    try:
        detected_lang = detect(msg)
    except:
        detected_lang = "en"

    if detected_lang == "bn" and "হ্যালো" in msg:
        return "হ্যালো! আমি EcoHusk চ্যাটবট। আপনি EcoHusk প্রকল্প সম্পর্কে কী জানতে চান?"

    if detected_lang == "zh-cn" and "你好" in msg:
        return "你好！我是EcoHusk聊天机器人。您想了解EcoHusk项目的哪些内容？"

    # Pass to RAG chain if not a simple greeting
    response = rag_chain.invoke({"input": msg})
    return str(response["answer"])





# Run the app
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
