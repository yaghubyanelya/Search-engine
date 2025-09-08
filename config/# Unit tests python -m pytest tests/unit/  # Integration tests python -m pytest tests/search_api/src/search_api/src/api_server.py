from flask import Flask, request, jsonify, render_template
from typing import Dict, List, Any
import logging
import time
import json
from ..indexer.src.inverted_index import InvertedIndex
from ..ranking.src.query_processor import QueryProcessor
from ..storage.src.document_store import DocumentStore

app = Flask(__name__)

class SearchAPI:
    """REST API for search functionality"""
    
    def __init__(self):
        self.inverted_index = InvertedIndex()
        self.query_processor = QueryProcessor()
        self.document_store = DocumentStore()
        self.logger = logging.getLogger(__name__)
        
        # Load index on startup
        try:
            self.inverted_index.load_from_file('data/inverted_index.pkl')
            self.logger.info("Search index loaded successfully")
        except FileNotFoundError:
            self.logger.warning("No existing index found. Please build index first.")
    
    def search_documents(self, query: str, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Search for documents matching query"""
        start_time = time.time()
        
        # Process query
        processed_query = self.query_processor.process_query(query)
        if not processed_query['terms']:
            return {
                'query': query,
                'total_results': 0,
                'page': page,
                'results': [],
                'processing_time': 0
            }
        
        # Search index
        search_results = self.inverted_index.search(
            processed_query['terms'], 
            limit=limit * 5  # Get more results for better ranking
        )
        
        # Get document details
        results = []
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        for doc_id, relevance_score in search_results[start_idx:end_idx]:
            doc_info = self.document_store.get_document_info(doc_id)
            if doc_info:
                results.append({
                    'title': doc_info.get('title', 'Untitled'),
                    'url': doc_info.get('url', ''),
                    'snippet': self._generate_snippet(doc_info.get('content', ''), processed_query['terms']),
                    'score': round(relevance_score, 4)
                })
        
        processing_time = time.time() - start_time
        
        return {
            'query': query,
            'processed_query': processed_query,
            'total_results': len(search_results),
            'page': page,
            'results': results,
            'processing_time': round(processing_time, 3)
        }
    
    def _generate_snippet(self, content: str, query_terms: List[str], max_length: int = 160) -> str:
        """Generate snippet highlighting query terms"""
        if not content or not query_terms:
            return content[:max_length] + "..." if len(content) > max_length else content
        
        # Find first occurrence of any query term
        content_lower = content.lower()
        first_match = len(content)
        
        for term in query_terms:
            pos = content_lower.find(term.lower())
            if pos != -1 and pos < first_match:
                first_match = pos
        
        # Extract snippet around first match
        start = max(0, first_match - max_length // 2)
        end = min(len(content), start + max_length)
        
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        
        return snippet
    
    def get_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Get autocomplete suggestions for partial query"""
        # Simple implementation - in production, use trie or specialized index
        suggestions = []
        
        # This would typically query a suggestion index
        # For now, return empty list
        return suggestions

# Initialize search API
search_api = SearchAPI()

@app.route('/search', methods=['GET'])
def search():
    """Search endpoint"""
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    if page < 1:
        return jsonify({'error': 'Page must be >= 1'}), 400
    
    if limit < 1 or limit > 100:
        return jsonify({'error': 'Limit must be between 1 and 100'}), 400
    
    try:
        results = search_api.search_documents(query, page, limit)
        return jsonify(results)
    
    except Exception as e:
        app.logger.error(f"Search error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/suggest', methods=['GET'])
def suggest():
    """Autocomplete suggestions endpoint"""
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 5))
    
    if not query:
        return jsonify({'suggestions': []})
    
    try:
        suggestions = search_api.get_suggestions(query, limit)
        return jsonify({'suggestions': suggestions})
    
    except Exception as e:
        app.logger.error(f"Suggestion error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/stats', methods=['GET'])
def stats():
    """Get search engine statistics"""
    try:
        index_stats = search_api.inverted_index.get_index_stats()
        return jsonify(index_stats)
    
    except Exception as e:
        app.logger.error(f"Stats error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'index_loaded': search_api.inverted_index.document_count > 0
    })

@app.route('/')
def index():
    """Serve web search interface"""
    return render_template('search.html')

if __name__ == '__main__':
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app.run(host='0.0.0.0', port=8080, debug=True)
