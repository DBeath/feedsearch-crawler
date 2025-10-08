# Contributing to feedsearch-crawler

Thank you for considering contributing to feedsearch-crawler! This document provides guidelines and instructions for contributing.

## Code of Conduct

This project follows a simple code of conduct: be respectful, constructive, and professional in all interactions.

## How to Contribute

### Reporting Bugs

Before creating a bug report:

- Check the existing issues to avoid duplicates
- Collect relevant information (Python version, OS, error messages, stack traces)

Create a detailed bug report including:

- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, dependencies)
- Minimal code example if applicable

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:

- Check existing issues and pull requests first
- Provide clear use case and rationale
- Consider implementation complexity and backward compatibility

### Pull Requests

1. **Fork the repository** and create a branch from `master`
2. **Set up development environment**:

   ```bash
   git clone https://github.com/YOUR_USERNAME/feedsearch-crawler.git
   cd feedsearch-crawler
   uv sync
   ```

3. **Make your changes**:
   - Write clear, documented code
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

4. **Test your changes**:

   ```bash
   # Run linting
   uv run ruff check
   uv run ruff format

   # Run tests
   uv run pytest

   # Check coverage
   uv run pytest --cov=src/feedsearch_crawler --cov-report=term-missing
   ```

5. **Commit your changes**:
   - Use clear, descriptive commit messages
   - Reference issue numbers when applicable
   - Follow conventional commits format (optional but appreciated)

6. **Submit a pull request**:
   - Provide clear description of changes
   - Link to related issues
   - Ensure CI checks pass

## Development Setup

### Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/DBeath/feedsearch-crawler.git
cd feedsearch-crawler

# Install dependencies
uv sync

# Run tests to verify setup
uv run pytest
```

### Development Commands

```bash
# Run linting checks
uv run ruff check

# Auto-format code
uv run ruff format

# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/feedsearch_crawler --cov-report=html

# Run specific test file
uv run pytest tests/crawler/test_request.py

# Run specific test
uv run pytest tests/crawler/test_request.py::TestRequest::test_initialization
```

### Running the Application

```bash
# Use default URLs from file
uv run main.py

# Crawl single URL
uv run main.py https://example.com

# Crawl multiple URLs
uv run main.py https://site1.com https://site2.com

# Get help
uv run main.py --help
```

## Code Style

### Python Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use [ruff](https://docs.astral.sh/ruff/) for linting and formatting
- Maximum line length: 88 characters (Black default)
- Use type hints for all functions and methods

### Code Organization

- Keep functions focused and single-purpose
- Add docstrings to public APIs
- Use meaningful variable and function names
- Avoid deep nesting (max 3-4 levels)

### Type Hints

This project uses type hints throughout. Please add type annotations to:

- All function parameters
- All function return types
- Class attributes where needed

## Testing

### Writing Tests

- Use pytest for all tests
- Add tests for all new functionality
- Aim for high code coverage (80%+ target)
- Test edge cases and error conditions
- Use descriptive test names

### Test Organization

```bash
tests/
├── crawler/          # Core crawler framework tests
├── feed_spider/      # Feed discovery tests
└── conftest.py       # Shared fixtures
```

### Async Testing

Use `pytest.mark.asyncio` for async tests:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected
```

## Documentation

### Code Documentation

- Add docstrings to all public classes and methods
- Use Google-style or NumPy-style docstrings
- Document parameters, return values, and exceptions
- Include usage examples for complex features

### Updating Documentation

- Update README.md for user-facing changes
- Update CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/) format
- Update type hints when changing function signatures

## Project Structure

```bash
feedsearch-crawler/
├── src/
│   └── feedsearch_crawler/
│       ├── crawler/          # Generic async crawler framework
│       │   ├── middleware/   # Request/response middleware
│       │   ├── crawler.py    # Base Crawler class
│       │   ├── downloader.py # HTTP client wrapper
│       │   ├── request.py    # Request class
│       │   └── response.py   # Response class
│       └── feed_spider/      # Feed discovery implementation
│           ├── spider.py     # FeedsearchSpider
│           ├── feed_info_parser.py
│           └── site_meta_parser.py
├── tests/                    # Test suite
├── main.py                   # CLI entry point
└── pyproject.toml           # Project configuration
```

## Release Process

Releases are handled by maintainers:

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create and push git tag
4. GitHub Actions automatically publishes to PyPI

## Questions?

- Check existing [issues](https://github.com/DBeath/feedsearch-crawler/issues)
- Review [README.md](README.md) for usage documentation
- Look at [CLAUDE.md](CLAUDE.md) for architecture overview

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
