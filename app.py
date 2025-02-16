import streamlit as st
import chromadb
import google.generativeai as genai
import os

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="college_website")

genai.configure(api_key=os.environ["GENAI_API_KEY"])
system_prompt = (
    "students by providing accurate information related to Hansraj College. "
    "When answering questions, refer to the provided context. If the query "
    "is not related to Hansraj College, simply state that you do not know "
    "about it."
)

model = genai.GenerativeModel("gemini-1.5-pro", system_instruction=system_prompt)

# Function to query ChromaDB and generate an answer

def query_chroma(query):
    results = collection.query(query_texts=[query], n_results=5)

    if not results['documents'][0]:
        return "I can only answer questions related to Hansraj College.", []

    context = "\n".join([doc for doc in results['documents'][0]])
    sources = [meta['source'] for meta in results['metadatas'][0]]

    # Generate response using Gemini
    prompt = f"{system_prompt}\nQuery: {query}\nContext: {context}"

    gemini_response = model.generate_content(prompt, stream=True)

    return gemini_response, sources

# Function to handle normal conversation without querying ChromaDB
def normal_conversation(query):
    prompt = (
        "You are an AI chatbot for Hansraj College. Respond casually to general "
        "inputs without referencing Hansraj College unless explicitly asked. "
        "If a question is unrelated to Hansraj College, politely say that you "
        "cannot provide information."
    )

    gemini_response = model.generate_content(f"{prompt}\n{query}", stream=True)
    return gemini_response

# Streamlit Chatbot UI
st.title("Hansraj College Chatbot")

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
user_query = st.chat_input("Ask a question about Hansraj College:")

if user_query:
    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # Check if the query is casual or college-related
    if "hansraj" in user_query.lower() or "college" in user_query.lower():
        answer_stream, sources = query_chroma(user_query)
    else:
        answer_stream = normal_conversation(user_query)
        sources = []

    # Display assistant response
    with st.chat_message("assistant"):
        response_text = ""
        response_container = st.empty()

        for chunk in answer_stream:
            if chunk.text:
                response_text += chunk.text
                response_container.markdown(response_text)

        if sources:
            st.markdown("**Sources:**")
            for source in sources:
                st.markdown(f"- [{source}]({source})")

    st.session_state.messages.append({"role": "assistant", "content": response_text})

