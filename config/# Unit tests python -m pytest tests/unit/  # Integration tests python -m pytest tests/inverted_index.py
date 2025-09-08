import pickle
import json
from typing import Dict, List, Set, Optional
from collections import defaultdict
import math
import logging

class InvertedIndex:
    """Inverted index implementation for fast text search"""
    
    def __init__(self):
        self.index: Dict[str, Dict[str, float]] = defaultdict(dict)  # term -> {doc_id: tf_idf}
        self.document_count = 0
        self.term_document_count: Dict[str, int] = defaultdict(int)  # term -> number of docs containing term
        self.document_lengths: Dict[str, int] = {}  # doc_id -> document length
        self.logger = logging.getLogger(__name__)
        
    def add_document(self, doc_id: str, terms: List[str]) -> None:
        """Add a document to the index"""
        if not terms:
            return
            
        # Calculate term frequencies
        term_freq = defaultdict(int)
        for term in terms:
            term_freq[term] += 1
        
        # Store document length
        self.document_lengths[doc_id] = len(terms)
        
        # Update term-document counts
        unique_terms = set(terms)
        for term in unique_terms:
            if doc_id not in self.index[term]:
                self.term_document_count[term] += 1
        
        # Calculate TF-IDF scores
        for term, freq in term_freq.items():
            tf = freq / len(terms)  # Term frequency
            self.index[term][doc_id] = tf
        
        self.document_count += 1
        self.logger.debug(f"Indexed document {doc_id} with {len(unique_terms)} unique terms")
    
    def calculate_tfidf_scores(self) -> None:
        """Calculate TF-IDF scores for all terms after all documents are added"""
        self.logger.info("Calculating TF-IDF scores...")
        
        for term, doc_scores in self.index.items():
            # Calculate IDF
            df = self.term_document_count[term]  # Document frequency
            idf = math.log(self.document_count / df) if df > 0 else 0
            
            # Update scores to TF-IDF
            for doc_id in doc_scores:
                tf = doc_scores[doc_id]
                self.index[term][doc_id] = tf * idf
    
    def search(self, query_terms: List[str], limit: int = 10) -> List[Tuple[str, float]]:
        """Search for documents matching query terms"""
        if not query_terms:
            return []
        
        # Get candidate documents
        candidate_docs: Set[str] = set()
        for term in query_terms:
            if term in self.index:
                candidate_docs.update(self.index[term].keys())
        
        if not candidate_docs:
            return []
        
        # Calculate relevance scores
        doc_scores = defaultdict(float)
        for term in query_terms:
            if term in self.index:
                for doc_id in candidate_docs:
                    if doc_id in self.index[term]:
                        doc_scores[doc_id] += self.index[term][doc_id]
        
        # Sort by relevance score
        results = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        return results[:limit]
    
    def get_term_stats(self, term: str) -> Dict:
        """Get statistics for a term"""
        if term not in self.index:
            return {"term": term, "document_count": 0, "total_frequency": 0}
        
        doc_count = len(self.index[term])
        total_freq = sum(self.index[term].values())
        
        return {
            "term": term,
            "document_count": doc_count,
            "total_frequency": total_freq,
            "idf": math.log(self.document_count / doc_count) if doc_count > 0 else 0
        }
    
    def save_to_file(self, filepath: str) -> None:
        """Save index to file"""
        data = {
            'index': dict(self.index),
            'document_count': self.document_count,
            'term_document_count': dict(self.term_document_count),
            'document_lengths': self.document_lengths
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        self.logger.info(f"Index saved to {filepath}")
    
    def load_from_file(self, filepath: str) -> None:
        """Load index from file"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.index = defaultdict(dict, data['index'])
        self.document_count = data['document_count']
        self.term_document_count = defaultdict(int, data['term_document_count'])
        self.document_lengths = data['document_lengths']
        
        self.logger.info(f"Index loaded from {filepath}")
    
    def get_index_stats(self) -> Dict:
        """Get overall index statistics"""
        total_terms = len(self.index)
        total_postings = sum(len(docs) for docs in self.index.values())
        
        return {
            "total_documents": self.document_count,
            "total_terms": total_terms,
            "total_postings": total_postings,
            "average_document_length": sum(self.document_lengths.values()) / len(self.document_lengths) if self.document_lengths else 0
        }
