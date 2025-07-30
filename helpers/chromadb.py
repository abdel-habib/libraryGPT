from langchain.vectorstores import Chroma

# Initialize Chroma database with collection support
def initialize_db(embedding_function, collection_name="default_collection"):
    """
    Initialize Chroma database with a specific collection name.
    :param collection_name: The name of the collection to work with
    :return: Chroma database instance
    """
    return Chroma(
        persist_directory="chroma_db",
        embedding_function=embedding_function,
        collection_name=collection_name
    )

# CREATE: Add new documents
def create_documents(db, documents):
    """
    Add new documents to the Chroma database.
    :param db: The Chroma database instance
    :param documents: List of strings to add to the database
    """
    metadatas = [{"id": i, "source": "user_input"} for i in range(len(documents))]
    db.add_texts(texts=documents, metadatas=metadatas)
    print("Documents added successfully.")

# READ: Query the database
def read_documents(db, query, k=3):
    """
    Query the database to find the most relevant documents.
    :param db: The Chroma database instance
    :param query: The query string
    :param k: Number of results to return
    """
    results = db.similarity_search(query, k=k)
    print("Query results:")
    for result in results:
        print(result)

# UPDATE: Update metadata or reindex a document (Re-indexing is a workaround for "updating")
def update_document(db, document_id, new_text):
    """
    Update a document by deleting and re-adding it.
    :param db: The Chroma database instance
    :param document_id: The ID of the document to update
    :param new_text: The new text to replace the old document
    """
    # Delete the document
    db.delete(ids=[document_id])
    # Re-add with new text
    db.add_texts(texts=[new_text], metadatas=[{"id": document_id, "source": "updated_input"}])
    print(f"Document {document_id} updated successfully.")

# DELETE: Remove documents from the database
def delete_documents(db, document_ids):
    """
    Remove documents by their IDs.
    :param db: The Chroma database instance
    :param document_ids: List of document IDs to delete
    """
    db.delete(ids=document_ids)
    print(f"Documents {document_ids} deleted successfully.")

# LIST COLLECTIONS: Get all collections in the database
def list_collections(embedding_function):
    """
    List all collections in the Chroma database.
    """
    db = Chroma(persist_directory="chroma_db", embedding_function=embedding_function)
    collections = db.get() #db.list_collections()

    return collections
    # print("Available collections:")
    # for collection in collections:
    #     print(collection)

# CHECK COLLECTION: Verify if a collection exists
def collection_exists(collection_name, embedding_function):
    """
    Check if a specific collection exists in the Chroma database.
    :param collection_name: The collection name to check
    :return: True if the collection exists, False otherwise
    """
    db = Chroma(persist_directory="chroma_db", embedding_function=embedding_function)
    collections = db.list_collections()
    return any(collection["name"] == collection_name for collection in collections)