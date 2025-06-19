# Truth-Focused Search Enhancement

**Created:** 2025-06-19 with user permission  
**Purpose:** Search system that prioritizes verified, accurate content and surfaces accuracy issues

**Intent:** This search enhancement system ensures users find working, tested information first while identifying and flagging potentially outdated or unverified content.

## Overview

The Truth-Focused Search Enhancement transforms documentation search from basic text matching to an intelligent system that understands content accuracy, verification status, and user success patterns.

## Core Search Enhancement Components

### 1. Verification-Aware Search Indexing

**Purpose:** Index content with accuracy metadata to enable truth-focused ranking

```python
class VerificationAwareIndexer:
    """Search indexer that includes content verification metadata"""
    
    def __init__(self, docs_path: str, verification_results_path: str):
        self.docs_path = Path(docs_path)
        self.verification_results = self.load_verification_results(verification_results_path)
        self.index = SearchIndex()
        
    def build_enhanced_index(self) -> Dict[str, Any]:
        """Build search index with verification metadata"""
        enhanced_index = {
            'documents': [],
            'verification_metadata': {},
            'accuracy_scores': {},
            'content_categories': {},
            'last_verified': {}
        }
        
        # Process all markdown files
        for md_file in self.docs_path.rglob("*.md"):
            doc_content = self.process_document(md_file)
            
            # Extract and verify code examples
            code_examples = self.extract_code_examples(doc_content['content'])
            verified_examples = self.verify_code_examples(code_examples, md_file)
            
            # Calculate document accuracy score
            accuracy_score = self.calculate_document_accuracy(
                md_file, verified_examples, doc_content
            )
            
            # Categorize content by type and verification status
            content_category = self.categorize_content(md_file, doc_content)
            
            # Build enhanced document record
            enhanced_doc = {
                'title': doc_content['title'],
                'content': doc_content['content'],
                'url': str(md_file.relative_to(self.docs_path)),
                'verification_status': self.get_verification_status(md_file),
                'accuracy_score': accuracy_score,
                'content_type': content_category,
                'code_examples_working': len(verified_examples['working']),
                'code_examples_broken': len(verified_examples['broken']),
                'last_verified': self.get_last_verification_date(md_file),
                'user_success_rate': self.get_user_success_rate(md_file),
                'search_keywords': self.extract_search_keywords(doc_content),
                'feature_status': self.get_feature_status(doc_content)
            }
            
            enhanced_index['documents'].append(enhanced_doc)
            enhanced_index['verification_metadata'][str(md_file)] = verified_examples
            enhanced_index['accuracy_scores'][str(md_file)] = accuracy_score
            
        return enhanced_index
    
    def calculate_document_accuracy(self, file_path: Path, verified_examples: Dict, 
                                  content: Dict) -> float:
        """Calculate accuracy score (0-1) for a document"""
        factors = {
            'code_examples_working': 0.4,      # 40% weight
            'links_functional': 0.3,           # 30% weight  
            'content_freshness': 0.2,          # 20% weight
            'user_feedback_positive': 0.1      # 10% weight
        }
        
        scores = {}
        
        # Code examples score
        total_examples = len(verified_examples['working']) + len(verified_examples['broken'])
        if total_examples > 0:
            scores['code_examples_working'] = len(verified_examples['working']) / total_examples
        else:
            scores['code_examples_working'] = 1.0  # No examples = no issues
        
        # Links score
        link_results = self.check_document_links(file_path)
        total_links = link_results['working'] + link_results['broken']
        if total_links > 0:
            scores['links_functional'] = link_results['working'] / total_links
        else:
            scores['links_functional'] = 1.0
        
        # Content freshness (based on last update vs related code changes)
        scores['content_freshness'] = self.calculate_freshness_score(file_path)
        
        # User feedback score
        scores['user_feedback_positive'] = self.get_user_feedback_score(file_path)
        
        # Calculate weighted average
        total_score = sum(scores[factor] * weight for factor, weight in factors.items())
        return total_score
    
    def categorize_content(self, file_path: Path, content: Dict) -> str:
        """Categorize content for targeted search"""
        path_str = str(file_path).lower()
        
        if 'getting_started' in path_str or 'quick_start' in path_str:
            return 'getting_started'
        elif 'tutorial' in path_str:
            return 'tutorial'
        elif 'api' in path_str or 'reference' in path_str:
            return 'reference'
        elif 'troubleshooting' in path_str:
            return 'troubleshooting'
        elif 'examples' in path_str:
            return 'examples'
        else:
            return 'general'
    
    def get_feature_status(self, content: Dict) -> Dict[str, str]:
        """Determine status of features mentioned in content"""
        feature_status = {}
        
        # Extract feature mentions
        features = self.extract_feature_mentions(content['content'])
        
        for feature in features:
            # Check if feature is available in current codebase
            if self.is_feature_available(feature):
                feature_status[feature] = 'available'
            elif self.is_feature_experimental(feature):
                feature_status[feature] = 'experimental'
            else:
                feature_status[feature] = 'unknown'
        
        return feature_status
```

**Index Enhancement Features:**
- Verification status for each document section
- Code example validation results
- Link health status
- Content freshness indicators
- User success rate data
- Feature availability mapping

### 2. Accuracy-Prioritized Search Ranking

**Purpose:** Rank search results to prioritize verified, working content

```python
class AccuracyAwareSearchRanker:
    """Search ranking algorithm that prioritizes accurate content"""
    
    def __init__(self, enhanced_index: Dict[str, Any]):
        self.index = enhanced_index
        self.ranking_weights = {
            'accuracy_score': 0.35,           # 35% - Most important
            'content_relevance': 0.25,        # 25% - Traditional relevance
            'content_type_boost': 0.15,       # 15% - Boost based on content type
            'user_success_rate': 0.15,        # 15% - User feedback
            'recency': 0.10                   # 10% - Content freshness
        }
    
    def search(self, query: str, user_context: Dict = None) -> List[SearchResult]:
        """Enhanced search with accuracy-based ranking"""
        
        # Step 1: Basic text matching
        text_matches = self.find_text_matches(query)
        
        # Step 2: Calculate accuracy-enhanced scores
        enhanced_results = []
        for match in text_matches:
            doc = self.get_document(match['document_id'])
            
            # Calculate component scores
            scores = {
                'accuracy_score': doc['accuracy_score'],
                'content_relevance': match['relevance_score'],
                'content_type_boost': self.get_content_type_boost(doc, query, user_context),
                'user_success_rate': doc['user_success_rate'],
                'recency': self.calculate_recency_score(doc['last_verified'])
            }
            
            # Calculate weighted final score
            final_score = sum(
                scores[component] * self.ranking_weights[component]
                for component in scores
            )
            
            enhanced_results.append(SearchResult(
                document=doc,
                query=query,
                final_score=final_score,
                component_scores=scores,
                verification_status=doc['verification_status'],
                accuracy_indicators=self.get_accuracy_indicators(doc)
            ))
        
        # Step 3: Sort by enhanced score
        enhanced_results.sort(key=lambda x: x.final_score, reverse=True)
        
        # Step 4: Apply post-processing filters
        filtered_results = self.apply_quality_filters(enhanced_results, user_context)
        
        return filtered_results
    
    def get_content_type_boost(self, doc: Dict, query: str, user_context: Dict) -> float:
        """Calculate boost based on content type and user context"""
        content_type = doc['content_type']
        
        # Default boosts for different content types
        type_boosts = {
            'getting_started': 0.9,      # High priority for beginners
            'tutorial': 0.8,             # High priority for learning
            'reference': 0.7,            # Medium priority
            'troubleshooting': 0.6,      # Lower unless problem-focused query
            'examples': 0.8,             # High for practical queries
            'general': 0.5               # Lowest priority
        }
        
        base_boost = type_boosts.get(content_type, 0.5)
        
        # Adjust based on query intent
        if self.is_problem_solving_query(query):
            if content_type == 'troubleshooting':
                base_boost += 0.3
            elif content_type == 'examples':
                base_boost += 0.2
                
        elif self.is_learning_query(query):
            if content_type in ['getting_started', 'tutorial']:
                base_boost += 0.2
        
        # Adjust based on user context
        if user_context and user_context.get('user_level') == 'beginner':
            if content_type == 'getting_started':
                base_boost += 0.3
            elif content_type == 'reference':
                base_boost -= 0.2
        
        return min(base_boost, 1.0)  # Cap at 1.0
    
    def get_accuracy_indicators(self, doc: Dict) -> Dict[str, Any]:
        """Generate accuracy indicators for search result display"""
        indicators = {}
        
        # Verification badge
        if doc['accuracy_score'] >= 0.9:
            indicators['verification_badge'] = 'verified'
        elif doc['accuracy_score'] >= 0.7:
            indicators['verification_badge'] = 'mostly_verified'
        else:
            indicators['verification_badge'] = 'needs_verification'
        
        # Code example status
        total_examples = doc['code_examples_working'] + doc['code_examples_broken']
        if total_examples > 0:
            if doc['code_examples_broken'] == 0:
                indicators['code_status'] = 'all_working'
            elif doc['code_examples_working'] > doc['code_examples_broken']:
                indicators['code_status'] = 'mostly_working'
            else:
                indicators['code_status'] = 'issues_detected'
        else:
            indicators['code_status'] = 'no_code'
        
        # Freshness indicator
        days_since_verified = (datetime.now() - doc['last_verified']).days
        if days_since_verified <= 7:
            indicators['freshness'] = 'very_fresh'
        elif days_since_verified <= 30:
            indicators['freshness'] = 'fresh'
        elif days_since_verified <= 90:
            indicators['freshness'] = 'moderate'
        else:
            indicators['freshness'] = 'outdated'
        
        return indicators
```

### 3. Feature Status Search Filters

**Purpose:** Allow users to filter search results by feature availability and status

```python
class FeatureStatusSearchFilter:
    """Search filters based on feature availability and implementation status"""
    
    def __init__(self, codebase_analyzer: CodebaseAnalyzer):
        self.codebase = codebase_analyzer
        self.feature_registry = self.build_feature_registry()
    
    def build_feature_registry(self) -> Dict[str, FeatureInfo]:
        """Build registry of all features and their current status"""
        registry = {}
        
        # Scan CLI tools
        cli_tools = self.codebase.get_cli_tools()
        for tool in cli_tools:
            registry[tool.name] = FeatureInfo(
                name=tool.name,
                type='cli_tool',
                status='available' if tool.is_functional() else 'broken',
                version_added=tool.version_added,
                documentation_paths=self.find_feature_documentation(tool.name)
            )
        
        # Scan library functions
        lib_functions = self.codebase.get_library_functions()
        for func in lib_functions:
            registry[func.name] = FeatureInfo(
                name=func.name,
                type='library_function',
                status='available' if func.is_tested() else 'untested',
                version_added=func.version_added,
                documentation_paths=self.find_feature_documentation(func.name)
            )
        
        # Scan validation rules
        validation_rules = self.codebase.get_validation_rules()
        for rule in validation_rules:
            registry[rule.name] = FeatureInfo(
                name=rule.name,
                type='validation_rule',
                status='active' if rule.is_enabled() else 'disabled',
                version_added=rule.version_added,
                documentation_paths=self.find_feature_documentation(rule.name)
            )
        
        return registry
    
    def filter_by_feature_status(self, search_results: List[SearchResult], 
                                status_filter: str) -> List[SearchResult]:
        """Filter search results by feature status"""
        
        if status_filter == 'verified_only':
            return [r for r in search_results if r.verification_status == 'verified']
        
        elif status_filter == 'working_examples_only':
            return [r for r in search_results 
                   if r.document['code_examples_broken'] == 0 and 
                      r.document['code_examples_working'] > 0]
        
        elif status_filter == 'available_features_only':
            filtered = []
            for result in search_results:
                # Check if all mentioned features are available
                mentioned_features = self.extract_mentioned_features(result.document['content'])
                if all(self.feature_registry.get(feat, {}).get('status') == 'available' 
                      for feat in mentioned_features):
                    filtered.append(result)
            return filtered
        
        elif status_filter == 'recent_only':
            cutoff_date = datetime.now() - timedelta(days=30)
            return [r for r in search_results 
                   if r.document['last_verified'] > cutoff_date]
        
        else:
            return search_results
```

### 4. Search Result Enhancement with Accuracy Indicators

**Purpose:** Display search results with clear accuracy and verification indicators

```html
<!-- Enhanced search result template -->
<div class="search-result" data-accuracy-score="{{ result.accuracy_score }}">
    <div class="result-header">
        <h3 class="result-title">
            <a href="{{ result.url }}">{{ result.title }}</a>
            <div class="verification-badges">
                {% if result.verification_status == 'verified' %}
                    <span class="badge badge-verified">✓ Verified</span>
                {% elif result.verification_status == 'partial' %}
                    <span class="badge badge-partial">~ Partial</span>
                {% else %}
                    <span class="badge badge-unverified">? Unverified</span>
                {% endif %}
                
                {% if result.code_status == 'all_working' %}
                    <span class="badge badge-code-working">⚡ Working Examples</span>
                {% elif result.code_status == 'issues_detected' %}
                    <span class="badge badge-code-issues">⚠ Code Issues</span>
                {% endif %}
                
                {% if result.freshness == 'very_fresh' %}
                    <span class="badge badge-fresh">🆕 Recently Verified</span>
                {% elif result.freshness == 'outdated' %}
                    <span class="badge badge-outdated">📅 Needs Update</span>
                {% endif %}
            </div>
        </h3>
    </div>
    
    <div class="result-content">
        <p class="result-excerpt">{{ result.excerpt }}</p>
        
        {% if result.featured_code_example %}
        <div class="result-code-preview">
            <h4>Working Example:</h4>
            <pre><code>{{ result.featured_code_example }}</code></pre>
            <span class="example-status">✅ Tested {{ result.example_last_tested }}</span>
        </div>
        {% endif %}
    </div>
    
    <div class="result-metadata">
        <span class="content-type">{{ result.content_type }}</span>
        <span class="accuracy-score">Accuracy: {{ result.accuracy_score|percentage }}</span>
        <span class="user-success">Success Rate: {{ result.user_success_rate|percentage }}</span>
        {% if result.related_features %}
            <div class="related-features">
                Features: 
                {% for feature in result.related_features %}
                    <span class="feature-tag feature-{{ feature.status }}">{{ feature.name }}</span>
                {% endfor %}
            </div>
        {% endif %}
    </div>
</div>
```

### 5. Intelligent Search Suggestions

**Purpose:** Provide smart suggestions based on accuracy and user success patterns

```python
class IntelligentSearchSuggester:
    """Provides intelligent search suggestions based on accuracy patterns"""
    
    def __init__(self, search_analytics: SearchAnalytics, accuracy_tracker: AccuracyTracker):
        self.analytics = search_analytics
        self.accuracy = accuracy_tracker
    
    def get_search_suggestions(self, partial_query: str, user_context: Dict) -> List[SearchSuggestion]:
        """Generate intelligent search suggestions"""
        suggestions = []
        
        # High-accuracy content suggestions
        high_accuracy_matches = self.find_high_accuracy_matches(partial_query)
        for match in high_accuracy_matches:
            suggestions.append(SearchSuggestion(
                text=match.suggested_query,
                type='high_accuracy',
                confidence=match.accuracy_score,
                description=f"Verified content with {match.accuracy_score:.0%} accuracy"
            ))
        
        # Popular successful searches
        successful_searches = self.analytics.get_successful_searches(partial_query)
        for search in successful_searches:
            suggestions.append(SearchSuggestion(
                text=search.query,
                type='popular_success',
                confidence=search.success_rate,
                description=f"Popular search with {search.success_rate:.0%} success rate"
            ))
        
        # Context-aware suggestions
        if user_context.get('user_level') == 'beginner':
            beginner_suggestions = self.get_beginner_friendly_suggestions(partial_query)
            suggestions.extend(beginner_suggestions)
        
        # Alternative phrasings for common failures
        failed_searches = self.analytics.get_failed_searches_similar_to(partial_query)
        for failed_search in failed_searches:
            better_alternative = self.find_better_alternative(failed_search.query)
            if better_alternative:
                suggestions.append(SearchSuggestion(
                    text=better_alternative.query,
                    type='improved_alternative',
                    confidence=better_alternative.success_rate,
                    description=f"Better alternative to '{failed_search.query}'"
                ))
        
        # Sort by confidence and relevance
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions[:8]  # Top 8 suggestions
    
    def suggest_accuracy_improvements(self, query: str, current_results: List[SearchResult]) -> List[str]:
        """Suggest ways to find more accurate results"""
        improvements = []
        
        # Check if results have accuracy issues
        low_accuracy_results = [r for r in current_results if r.accuracy_score < 0.7]
        
        if low_accuracy_results:
            improvements.append("Try adding 'verified' or 'working' to find tested examples")
            improvements.append("Filter by 'recent' to get up-to-date information")
        
        # Check for feature availability issues
        unavailable_features = self.find_unavailable_features_in_results(current_results)
        if unavailable_features:
            improvements.append(f"Some results mention unavailable features: {', '.join(unavailable_features)}")
            improvements.append("Try searching for alternative approaches")
        
        # Check for outdated content
        outdated_results = [r for r in current_results 
                          if (datetime.now() - r.document['last_verified']).days > 90]
        if outdated_results:
            improvements.append("Some results may be outdated - try filtering by 'recent'")
        
        return improvements
```

## Search Analytics and Feedback Integration

### 1. Search Success Tracking

```python
class SearchSuccessTracker:
    """Track search success patterns to improve accuracy-focused ranking"""
    
    def track_search_interaction(self, query: str, clicked_result: SearchResult, 
                                outcome: str, user_context: Dict):
        """Track user interactions with search results"""
        interaction = SearchInteraction(
            query=query,
            result_url=clicked_result.url,
            result_accuracy_score=clicked_result.accuracy_score,
            outcome=outcome,  # 'success', 'partial_success', 'failure'
            user_context=user_context,
            timestamp=datetime.now()
        )
        
        self.store_interaction(interaction)
        
        # Update result quality scores
        if outcome == 'success':
            self.boost_result_score(clicked_result.url, query)
        elif outcome == 'failure':
            self.penalize_result_score(clicked_result.url, query)
    
    def generate_search_quality_report(self) -> Dict[str, Any]:
        """Generate report on search quality and accuracy correlation"""
        interactions = self.get_recent_interactions(days=30)
        
        # Analyze accuracy score vs success rate
        accuracy_success_correlation = self.calculate_accuracy_success_correlation(interactions)
        
        # Identify problematic content
        problematic_results = self.find_high_failure_rate_results(interactions)
        
        # Suggest ranking improvements
        ranking_suggestions = self.suggest_ranking_improvements(interactions)
        
        return {
            'total_searches': len(interactions),
            'accuracy_success_correlation': accuracy_success_correlation,
            'problematic_results': problematic_results,
            'ranking_suggestions': ranking_suggestions,
            'top_successful_queries': self.get_top_successful_queries(interactions),
            'top_failed_queries': self.get_top_failed_queries(interactions)
        }
```

## Integration with Verification Pipeline

### Search Index Updates on Verification

```python
def update_search_index_on_verification(verification_results: Dict[str, Any]):
    """Update search index when verification results change"""
    
    search_indexer = VerificationAwareIndexer()
    
    for file_path, verification_data in verification_results.items():
        # Update accuracy score
        new_accuracy_score = calculate_accuracy_from_verification(verification_data)
        search_indexer.update_document_accuracy(file_path, new_accuracy_score)
        
        # Update verification status
        verification_status = determine_verification_status(verification_data)
        search_indexer.update_verification_status(file_path, verification_status)
        
        # Update code example status
        code_status = extract_code_example_status(verification_data)
        search_indexer.update_code_status(file_path, code_status)
    
    # Rebuild search index with new accuracy data
    search_indexer.rebuild_index()
    
    # Notify search service of updates
    search_service.refresh_index()
```

## Search Interface Enhancements

### Advanced Search Filters
- **Verification Status**: Verified, Partially Verified, Unverified
- **Code Examples**: Working Examples Only, All Content
- **Content Freshness**: Last 7 days, Last 30 days, Last 90 days
- **Feature Status**: Available Features Only, All Features
- **Content Type**: Getting Started, Tutorials, Reference, Examples
- **User Success Rate**: High Success (>80%), Medium Success (>60%), All

### Search Result Sorting Options
- **Relevance + Accuracy** (default): Balanced ranking
- **Accuracy First**: Highest accuracy scores first
- **Most Recent**: Recently verified content first
- **User Success**: Highest user success rates first
- **Traditional Relevance**: Text matching only

This truth-focused search enhancement ensures users find accurate, working information while identifying content that needs attention, dramatically improving the documentation user experience.