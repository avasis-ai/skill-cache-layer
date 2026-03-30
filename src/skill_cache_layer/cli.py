"""CLI entry point for skill-cache-layer."""

import click
import httpx

from skill_cache_layer.semantic_cache import SemanticCache


@click.group()
@click.version_option(version="0.1.0", prog_name="skill-cache-layer")
def cli():
    """Skill Cache Layer - Sub-millisecond semantic memory retrieval."""
    pass


@cli.command()
@click.argument("skill_name")
@click.argument("input_text")
@click.option("--cache-path", default="skill_cache.pkl", help="Path to cache file")
def search(skill_name: str, input_text: str, cache_path: str) -> None:
    """Search for a cached result.

    Example:
        skill-cache-layer search "code_analysis" "Analyze this Python file"
    """
    cache = SemanticCache(cache_path=cache_path)
    result = cache.get(skill_name, input_text)

    if result is None:
        click.echo("No cached result found")
        return

    click.echo(f"Found cached result for '{skill_name}':")
    click.echo(result)


@cli.command()
@click.argument("skill_name")
@click.argument("input_text")
@click.argument("result")
@click.option("--cache-path", default="skill_cache.pkl", help="Path to cache file")
def add(skill_name: str, input_text: str, result: str, cache_path: str) -> None:
    """Add a new cached entry.

    Example:
        skill-cache-layer add "code_analysis" "Analyze this file" '{"result": "OK"}'
    """
    cache = SemanticCache(cache_path=cache_path)
    cache.add(skill_name, input_text, result)
    cache.save()

    click.echo(f"Added cache entry for '{skill_name}'")


@cli.command()
@click.option("--cache-path", default="skill_cache.pkl", help="Path to cache file")
def stats(cache_path: str) -> None:
    """Get cache statistics."""
    cache = SemanticCache(cache_path=cache_path)
    stats = cache.stats()

    click.echo(f"Cache Statistics:")
    click.echo(f"  Total entries: {stats['total_entries']}")
    click.echo(f"  Cache size: {stats['cache_size_bytes']} bytes")
    click.echo(f"  Skills tracked: {len(stats['skills'])}")
    click.echo(f"  Skills: {', '.join(stats['skills'])}")


@cli.command()
@click.option("--cache-path", default="skill_cache.pkl", help="Path to cache file")
def clear(cache_path: str) -> None:
    """Clear all cache entries."""
    cache = SemanticCache(cache_path=cache_path)
    cache.clear()
    click.echo("Cache cleared")


@cli.command()
@click.option("--cache-path", default="skill_cache.pkl", help="Path to cache file")
def serve(cache_path: str) -> None:
    """Start the API server.

    Runs a FastAPI server on port 8000 with full cache functionality.
    """
    import uvicorn
    from pathlib import Path

    cache_instance_path = Path(cache_path)

    # Import here to avoid circular imports
    from skill_cache_layer.api import cache_instance as api_cache, app

    # Override cache path for API
    import skill_cache_layer.api as api_module
    api_module.cache_instance = SemanticCache(cache_path=str(cache_instance_path))

    click.echo(f"Starting API server at http://0.0.0.0:8000")
    click.echo(f"Cache file: {cache_instance_path}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


@cli.command()
@click.option("--cache-path", default="skill_cache.pkl", help="Path to cache file")
def demo(cache_path: str) -> None:
    """Run a demo showing cache functionality."""
    from skill_cache_layer.semantic_cache import SemanticCache

    cache = SemanticCache(cache_path=cache_path)

    # Simulate some skill executions
    skill_name = "code_analysis"

    # First call - will add to cache
    click.echo("\n1. First analysis (will be cached):")
    input_text = "Analyze this Python file for security vulnerabilities"
    result1 = {"vulnerabilities": ["none"], "score": 95}
    cache.add(skill_name, input_text, result1)

    # Second call - will find in cache
    click.echo("\n2. Same analysis (will hit cache):")
    result2 = cache.get(skill_name, input_text)
    if result2:
        click.echo(f"  ✓ Cache hit! Result: {result2}")

    # Third call - different input
    click.echo("\n3. Different analysis (new entry):")
    input_text3 = "Review this code for performance issues"
    result3 = {"issues": ["loop_optimization"], "score": 87}
    cache.add(skill_name, input_text3, result3)
    click.echo(f"  Added new entry")

    # Show stats
    click.echo("\n4. Cache statistics:")
    stats = cache.stats()
    click.echo(f"  Total entries: {stats['total_entries']}")

    # Save cache
    cache.save()
    click.echo(f"\n✓ Demo complete. Cache saved to {cache_path}")


if __name__ == "__main__":
    cli()
