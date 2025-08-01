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
import shutil

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

# Set embedding_function to None if using SentenceTransformer #=embedding_model,
# SentenceTransformer does not normalise, so we need to normalise the embeddings in a later stage for cosine similarity
# https://github.com/langchain-ai/langchain/discussions/18489 L2/Euclidean > cosine dist & collection_metadata={"hnsw:space": "cosine"} > cos sim = 1 - dist
# https://github.com/UKPLab/sentence-transformers/issues/2261 embedding normalization, removing th embedding_function from using the embedding_model

# embedding_model = OpenAIEmbeddings() # Openai
# embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")  # Load SentenceTransformers model

# Clear the database at startup
chroma_db_path = "./chroma_db"
collection_name = 'pdf_embeddings'
vectorstore = None  # Global handle

# Text splitter configuration
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # Number of characters per chunk
    chunk_overlap=100,  # Overlap between chunks to maintain context
)

@app.route("/")
def index():
    # return the json file with the template
    return render_template('index.html')

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
    global vectorstore

    try:
        data = request.get_json()
        if not data or "directory" not in data:
            return jsonify({"error": "Missing 'directory' in request body"}), 400

        directory = data["directory"]

        if not os.path.exists(directory):
            return jsonify({"error": "Directory does not exist"}), 400
        
        # Delete existing collection (if it exists)
        try:
            temp_vs = Chroma(
                persist_directory=chroma_db_path,
                embedding_function=embedding_model
            )
            temp_vs._client.delete_collection(name=collection_name)
        except Exception as e:
            print(f"Error deleting existing collection: {e}")

        # Recreate vectorstore with the same collection name
        vectorstore = Chroma(
            persist_directory=chroma_db_path,
            collection_name=collection_name,
            embedding_function=embedding_model,
            collection_metadata={"hnsw:space": "cosine"}
        )

        pdf_files = [file for file in os.listdir(directory) if file.lower().endswith('.pdf')]
        if not pdf_files:
            return jsonify({"error": "No PDF files found in the directory"}), 400

        for file in pdf_files:
            try:
                with open(os.path.join(directory, file), 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    pdf_full_text = ''.join(page.extract_text() or '' for page in reader.pages)
                    pdf_chunks = text_splitter.split_text(pdf_full_text)

                    pdf_documents = [
                        Document(
                            page_content=chunk,
                            metadata={
                                "file_name": os.path.basename(file),
                                "chunk_index": idx
                            }
                        )
                        for idx, chunk in enumerate(pdf_chunks)
                    ]

                    vectorstore.add_documents(pdf_documents)

            except Exception as e:
                app.logger.error(f"Error processing file '{file}': {e}")
                return jsonify({"error": f"Error processing file '{file}'"}), 500

        return jsonify({'message': 'Embeddings generated successfully'}), 200

    except Exception as e:
        app.logger.exception("Unhandled exception during embedding generation")
        return jsonify({"error": "Internal server error occurred"}), 500
    

@app.route('/search-documents', methods=['POST'])
def search():
    global vectorstore

    try:
        query = request.json.get("query")
        top_k = request.json.get("top_k", 5)

        if not query:
            return jsonify({"error": "Query not provided"}), 400

        if not vectorstore:
            return jsonify({"error": "No embeddings available. Please generate embeddings first."}), 400

        results = vectorstore.similarity_search_with_score(query, k=int(top_k))

        response = [
            {
                "text": result[0].page_content,
                "file_name": result[0].metadata.get("file_name"),
                "chunk_index": result[0].metadata.get("chunk_index"),
                "similarity": 1 - result[1]
            } for result in results
        ]

        response.sort(key=lambda x: x["similarity"], reverse=True)

        return jsonify(response), 200

    except Exception as e:
        app.logger.exception("Search failed")
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