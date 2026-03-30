# AGENTS.md - Agent Configuration

## Skill Cache Layer

This is **Agent #26** - the semantic cache layer for agent skills.

### Configuration

- **Name**: skill-cache-layer
- **Purpose**: Semantic caching for skill execution
- **Domain**: LLM API optimization, caching, performance acceleration

### Capabilities

- Semantic similarity-based caching
- Sub-millisecond cache lookups
- Persistent cache storage
- FastAPI server deployment
- CLI interface for cache management

### Usage

This agent should be used for:

- Reducing LLM API costs
- Improving agent response times
- Handling repetitive skill patterns
- Stateless skill execution optimization

### Cache Strategy

- **Threshold**: 0.85 similarity for cache hits
- **Storage**: Persistent file-based cache
- **Vector Space**: 384-dimensional embeddings
- **Refresh**: Automatic on changes

### Performance Targets

- **Cache Hit**: <1ms
- **Cache Miss**: LLM API latency
- **Memory**: Linear with entries
- **Disk**: ~2KB per entry

### API Endpoints

- `/api/search` - Search cached results
- `/api/add` - Add new cache entries
- `/api/stats` - Get cache statistics
- `/api/clear` - Clear cache

---

For more information, see [README.md](README.md).
