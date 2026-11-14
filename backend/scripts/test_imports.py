import sys
print("Importing pymupdf...")
import fitz
print("Importing chunker...")
from app.rag.chunker import DocumentChunker
print("Importing embeddings...")
from app.rag.embeddings import SentenceTransformerEmbeddings
print("Importing vectorstore...")
from app.rag.vectorstore import ChromaVectorStore
print("Importing generator...")
from app.rag.generator import RAGGenerator
print("Importing service...")
from app.rag.service import RAGService
print("Importing evaluator...")
from app.rag.evaluator import RAGEvaluator
print("ALL RAG MODULES IMPORTED SUCCESSFULLY!")

