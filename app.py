from flask import (
    Flask, 
    request,
    jsonify,
    render_template,
    send_file
    )
import os
from io import BytesIO
import json
from dotenv import load_dotenv
from helpers.pdf_preview import return_pdf_preview_html
import PyPDF2

# from sentence_transformers import SentenceTransformer
from langchain_huggingface import HuggingFaceEmbeddings 
# from langchain.embeddings import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

app = Flask(__name__)

# UPLOAD_FOLDER = './uploads'
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

load_dotenv()
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER')
WOKSPACE_JSON = os.getenv('WORKSPACE_JSON')

# Set embedding_function to None if using SentenceTransformer #=embedding_model,
# SentenceTransformer does not normalise, so we need to normalise the embeddings in a later stage for cosine similarity
# https://github.com/langchain-ai/langchain/discussions/18489 L2/Euclidean > cosine dist & collection_metadata={"hnsw:space": "cosine"} > cos sim = 1 - dist
# https://github.com/UKPLab/sentence-transformers/issues/2261 embedding normalization, removing th embedding_function from using the embedding_model

# embedding_model = OpenAIEmbeddings() # Openai
# embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")  # Load SentenceTransformers model

chroma_db_path = "./chroma_db"  # Path to store Chroma database
vectorstore = Chroma(
    persist_directory=chroma_db_path, 
    embedding_function = embedding_model,
    collection_metadata={"hnsw:space": "cosine"}  # Define the metadata to change the distance function to cosine
    )

# Text splitter configuration
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # Number of characters per chunk
    chunk_overlap=100,  # Overlap between chunks to maintain context
)

@app.route("/")
def hello_world():
    # read the json file
    with open(WOKSPACE_JSON) as f:
        data = json.load(f)

    # return the json file with the template
    return render_template('index.html', workspace_json=data)

# @app.route('/upload', methods=['POST'])
# def upload_file():
#     if 'files' not in request.files:
#         return jsonify({'error': 'No files part in the request'}), 400
    
#     files = request.files.getlist('files')
#     saved_files = []
    
#     for file in files:
#         if file.filename.endswith('.pdf'):
#             filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
#             file.save(filepath)
#             saved_files.append(file.filename)
#         else:
#             return jsonify({'error': 'Only PDF files are allowed'}), 400
    
#     return jsonify({'message': 'Files uploaded successfully', 'files': saved_files}), 200


@app.route('/generate-embeddings', methods=['POST'])
def generate_pdfs_embeddings():
    try:
        files_directories = request.json.get("files_directories")

        if len(files_directories) == 0:
            return jsonify({'error': 'No files selected'}), 400
        
        for file in files_directories:
            with open(file, 'rb') as f:
                # read the pdf
                reader = PyPDF2.PdfReader(f)

                # concat all text
                pdf_full_text = ''.join(page.extract_text() for page in reader.pages)

                # split into chuncks
                pdf_chunks = text_splitter.split_text(pdf_full_text)

                # Create Document objects for each chunk
                pdf_documents = [
                    Document(page_content=chunk, 
                             metadata={
                                 "file_name": file.split('\\')[-1], 
                                 "chunk_index": idx
                                 })
                    for idx, chunk in enumerate(pdf_chunks)
                ]
                
                try:
                    # Add the documents to the Chroma database (embedding is handled by Chroma's embedding_function)
                    vectorstore.add_documents(pdf_documents)

                except Exception as e:
                    print(f"Error adding documents to Chroma: {e}")
                    return jsonify({"error": str(e)}), 500

        # Persist the vectorstore to disk 
        # This is important to save the embeddings and documents
        # If you don't persist, the embeddings will be lost when the app restarts               
        vectorstore.persist()

        return jsonify({'message': 'Embeddings generated successfully'}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/search-documents', methods=['POST'])
def search():
    try:
        # Get query and top_k from the request
        query = request.json.get("query")
        top_k = request.json.get("top_k", 5)

        if not isinstance(top_k, int):
            top_k = int(top_k)
        
        try:
            # Perform similarity search and retrieve scores
            results = vectorstore.similarity_search_with_score(query, k=top_k)
        except Exception as e:
            raise ValueError(f"Error in similarity search: {e}")

        # Format the response with confidence scores
        response = [
            {
                "text": result[0].page_content,
                "file_name": result[0].metadata.get("file_name"),
                "chunk_index": result[0].metadata.get("chunk_index"),
                "similarity": 1 - result[1] # Convert cosine distance to cosine similarity
            } for result in results
        ]

        response = sorted(response, key=lambda x: x["similarity"], reverse=True)

        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get-pdfs-preview', methods=['POST'])
def get_pdfs():
    data = request.get_json()['selectedOption']
    
    pdf_files = [file for file in os.listdir(data) if file.lower().endswith('.pdf')]

    if not pdf_files:
        return jsonify({"error": "No PDF files found"}), 400

    pdf_with_previews = []

    for file_path in pdf_files:
        full_file_path = os.path.join(data, file_path)
        
        pdf_with_previews.append({
            'file_path': full_file_path,
            'file_name': file_path,
            'data_url': return_pdf_preview_html(full_file_path)
        })

    return jsonify({
        'pdf_files': pdf_with_previews,
    })

if __name__ == '__main__': 
    app.run(host='0.0.0.0', debug=True)