import os
import torch
from pinecone import Pinecone
from transformers import AutoTokenizer, AutoModel
from dotenv import load_dotenv
from pinecone import ServerlessSpec
from sentence_transformers import SentenceTransformer

load_dotenv()

# ✅ Global variables for memory efficiency
tokenizer = None
model = None

def get_model():
    global model
    if model is None:
        print("🔄 Loading embedding model...")
        # model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        # ✅ Force CPU usage for deployment
        model.eval()  # Set to evaluation mode
        print("✅ Model loaded successfully")
    return model

def get_tokenizer():
    global tokenizer
    if tokenizer is None:
        print("🔄 Loading tokenizer...")
        # tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        print("✅ Tokenizer loaded successfully")
    return tokenizer

class PineconeManager:
    def __init__(self):
        """
        pinecone is the vector database used to store the curriculum document in vector
        pinecone manager contructor that set the environment variable needed to use pinecone
        - pinecone api key
        - pinecone index name
        - used pretrained sentence-transformer/allMini-L6-V2 model for embedding
        - used pretrained tokenizer sentence-transformers/all-MiniLM-L6-v2 for tokenization
        """
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = os.getenv("PINECONE_INDEX")
        self.tokenizer = get_tokenizer()
        self.model = get_model()

        #move the model to the available processor
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # Initialize index - create index if its not in the vector database
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=self.index_name, #index name
                dimension=384, #vector dimension
                metric="cosine", #cosine similarity used
                spec=ServerlessSpec(cloud="aws", region="us-east-1") #database cloud location 
            )

        #if it's there just use the available one   
        self.index = self.pc.Index(self.index_name)



    # def upsert_content(self, chunks, metadata, country: str = "nigeria"):
    #     if len(chunks) != len(metadata):
    #         raise ValueError("Chunks and metadata lists must have the same length")
            
    #     embeddings = []
    #     for i, (chunk, meta) in enumerate(zip(chunks, metadata)):
    #         inputs = self.tokenizer(chunk, return_tensors="pt", padding=True, truncation=True)
    #         inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
    #         with torch.no_grad():
    #             embedding = self.model(**inputs).last_hidden_state.mean(dim=1)
            
    #         # KEEP the extracted metadata instead of overwriting it
    #         full_metadata = {
    #             "content": chunk,
    #             "country": country,  # Add country field
    #             "chunk_index": i,
    #             **meta  # This preserves subject, grade_level, etc.
    #         }
            
    #         embeddings.append({
    #             # "id": f"chunk-{hash(chunk)}-{i}",  # More unique ID
    #             "id": f"chunk-{country}-{hash(chunk)}-{i}",  # Include country in ID
    #             "values": embedding[0].tolist(),
    #             "metadata": full_metadata
    #         })
        
    #     # ✅ Add error handling and return confirmation
    #     try:
    #         self.index.upsert(embeddings)
    #         print(f"✅ Successfully upserted {len(embeddings)} vectors to Pinecone")
    #         return {"status": "success", "vectors_upserted": len(embeddings)}
    #     except Exception as e:
    #         print(f"❌ Error upserting to Pinecone: {e}")
    #         raise e

    def upsert_content(self, chunks, metadata, country: str = "nigeria"):
        if len(chunks) != len(metadata):
            raise ValueError("Chunks and metadata lists must have the same length")
            
        embeddings = []
        
        # ✅ Process in smaller batches to reduce memory usage
        batch_size = 5  # Process 5 chunks at a time
        
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_metadata = metadata[i:i + batch_size]
            
            for j, (chunk, meta) in enumerate(zip(batch_chunks, batch_metadata)):
                # ✅ Use global tokenizer and model
                inputs = self.tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=512)
                
                with torch.no_grad():
                    embedding = self.model(**inputs).last_hidden_state.mean(dim=1)
                
                full_metadata = {
                    "content": chunk,
                    "country": country,
                    "chunk_index": i + j,
                    **meta
                }
                
                embeddings.append({
                    "id": f"chunk-{country}-{hash(chunk)}-{i + j}",
                    "values": embedding[0].tolist(),
                    "metadata": full_metadata
                })
            
            # ✅ Clear cache after each batch
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
        
        # ✅ Add error handling and return confirmation
        try:
            self.index.upsert(embeddings)
            print(f"✅ Successfully upserted {len(embeddings)} vectors to Pinecone")
            return {"status": "success", "vectors_upserted": len(embeddings)}
        except Exception as e:
            print(f"❌ Error upserting to Pinecone: {e}")
            raise e