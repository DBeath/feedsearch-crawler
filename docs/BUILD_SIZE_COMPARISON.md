# Build Size Comparison: Current vs Pydantic

**Created:** 2025-01-16
**Updated:** 2025-01-16

---

This document compares the package size and dependency footprint of the current implementation versus adopting Pydantic V2 for serialization.

## Current Implementation

### Package Size

```bash
# Build the current package
uv build

# Check wheel size
ls -lh dist/*.whl
```

**Expected output:**
```
feedsearch_crawler-1.0.3-py3-none-any.whl    ~50-60 KB
feedsearch_crawler-1.0.3.tar.gz             ~70-80 KB
```

### Dependencies (from pyproject.toml)

**Runtime dependencies:**
```toml
dependencies = [
    "aiohttp>3.12.0",           # ~1.5 MB
    "beautifulsoup4>=4.14.2",   # ~500 KB
    "aiodns>=3.2.0",            # ~50 KB
    "uvloop>=0.19.0",           # ~3 MB (compiled extension)
    "w3lib>=2.1.2",             # ~100 KB
    "feedparser>=6.0.12",       # ~200 KB
    "brotlipy>=0.7.0",          # ~400 KB
    "python-dateutil>=2.9.0",   # ~300 KB
    "yarl>=1.22.0",             # ~200 KB
    "asyncio>=3.4.3",           # stdlib (no size impact)
]
```

**Total approximate installed size: ~6.5 MB**

### Dependency Tree

```
feedsearch-crawler (60 KB)
├── aiohttp (1.5 MB)
│   ├── aiosignal
│   ├── attrs
│   ├── frozenlist
│   ├── multidict
│   └── yarl
├── beautifulsoup4 (500 KB)
│   └── soupsieve
├── feedparser (200 KB)
│   └── sgmllib3k
├── uvloop (3 MB)
├── w3lib (100 KB)
├── brotlipy (400 KB)
│   └── cffi
├── python-dateutil (300 KB)
│   └── six
├── aiodns (50 KB)
│   └── pycares
└── yarl (200 KB)
    └── multidict
```

**Dependency count: 9 direct + ~15 transitive = ~24 total packages**

---

## With Pydantic V2

### Package Size

```bash
# After implementing Pydantic
# The package itself would be similar in size
```

**Expected output:**
```
feedsearch_crawler-2.0.0-py3-none-any.whl    ~55-65 KB (+5-10 KB)
```

The code itself wouldn't grow much, but dependency installation would be significantly larger.

### Dependencies (with Pydantic)

**Runtime dependencies:**
```toml
dependencies = [
    # All current dependencies remain
    "aiohttp>3.12.0",
    "beautifulsoup4>=4.14.2",
    "aiodns>=3.2.0",
    "uvloop>=0.19.0",
    "w3lib>=2.1.2",
    "feedparser>=6.0.12",
    "brotlipy>=0.7.0",
    "python-dateutil>=2.9.0",
    "yarl>=1.22.0",

    # NEW: Pydantic V2
    "pydantic>=2.0.0",          # ~500 KB (pure Python)
    "pydantic-core>=2.0.0",     # ~8-10 MB (Rust compiled)
    "typing-extensions",        # ~100 KB
]
```

**Total approximate installed size: ~17 MB (+10.5 MB = 162% increase)**

### Dependency Tree with Pydantic

```
feedsearch-crawler (65 KB)
├── [all current dependencies] (~6.5 MB)
└── pydantic (500 KB)
    ├── pydantic-core (10 MB) ⚠️ LARGE
    ├── typing-extensions (100 KB)
    └── annotated-types (50 KB)
```

**Dependency count: 12 direct + ~18 transitive = ~30 total packages (+6 packages)**

---

## Comparison Table

| Metric | Current | With Pydantic | Difference |
|--------|---------|---------------|------------|
| **Package Size (.whl)** | ~60 KB | ~65 KB | +8% |
| **Installed Dependencies** | ~6.5 MB | ~17 MB | +162% |
| **Direct Dependencies** | 9 | 12 | +33% |
| **Total Package Count** | ~24 | ~30 | +25% |
| **Largest Dependency** | uvloop (3 MB) | pydantic-core (10 MB) | +233% |

---

## Impact Analysis

### For Library Users

**Current implementation:**
```bash
pip install feedsearch-crawler
# Downloads: ~6.5 MB
# Install time: ~5-10 seconds
# Disk space: ~6.5 MB
```

**With Pydantic:**
```bash
pip install feedsearch-crawler[pydantic]  # if optional
# OR
pip install feedsearch-crawler  # if required
# Downloads: ~17 MB
# Install time: ~10-20 seconds
# Disk space: ~17 MB
```

### Docker Image Size Impact

```dockerfile
# Current
FROM python:3.12-slim
RUN pip install feedsearch-crawler
# Image size increase: +6.5 MB

# With Pydantic
FROM python:3.12-slim
RUN pip install feedsearch-crawler
# Image size increase: +17 MB (+10.5 MB more)
```

### AWS Lambda Package Size

**Current:**
- Lambda layer: ~6.5 MB (compressed)
- Well under 50 MB limit ✅

**With Pydantic:**
- Lambda layer: ~17 MB (compressed)
- Still under limit but 2.6x larger ⚠️

---

## Alternative: cattrs

### Dependencies with cattrs

```toml
dependencies = [
    # All current dependencies
    "cattrs>=23.0.0",           # ~200 KB
]
```

**Total approximate installed size: ~7 MB (+0.5 MB = 7.7% increase)**

### Comparison: cattrs vs Pydantic

| Metric | Current | + cattrs | + Pydantic |
|--------|---------|----------|------------|
| **Total Size** | 6.5 MB | 7 MB | 17 MB |
| **Increase** | baseline | +8% | +162% |
| **Docker Impact** | baseline | minimal | significant |

---

## Recommendations

### For This Library

Given that feedsearch-crawler is a **library consumed by other projects**, dependencies have cascading effects:

#### Option 1: Keep Current (Recommended)
✅ **Pros:**
- Minimal dependency footprint
- No breaking changes
- Fast installation
- Docker-friendly

❌ **Cons:**
- Manual serialization maintenance
- No automatic validation

#### Option 2: Add cattrs (Moderate)
✅ **Pros:**
- Only +0.5 MB (+8%)
- Automatic serialization
- Minimal impact on users

❌ **Cons:**
- Another dependency to maintain
- Manual validation still needed

#### Option 3: Add Pydantic (Not Recommended)
✅ **Pros:**
- Industry standard
- Excellent validation
- JSON Schema generation

❌ **Cons:**
- +10.5 MB (+162%) dependency bloat
- Impacts ALL downstream users
- Potential version conflicts
- Slower installation

### General Guidelines

**Use Pydantic when:**
- Building an end-user application
- Validation is critical to business logic
- Ecosystem integration is important
- Size doesn't matter (cloud services)

**Avoid Pydantic when:**
- Building a library package (like this)
- Minimizing dependencies is important
- Used in resource-constrained environments
- Docker image size matters

---

## Measuring Actual Sizes

To measure the actual size for your specific version:

```bash
# Build current version
uv build
ls -lh dist/

# Create virtual env and measure
python -m venv test_env
source test_env/bin/activate
pip install ./dist/feedsearch_crawler-*.whl
du -sh test_env/lib/python3.12/site-packages/

# Measure with Pydantic (hypothetical)
pip install pydantic
du -sh test_env/lib/python3.12/site-packages/
```

### Example Script

```bash
#!/bin/bash
# measure_deps.sh - Measure dependency sizes

echo "=== Current Implementation ==="
uv sync
du -sh .venv/ | awk '{print "Total venv: " $1}'

echo -e "\n=== With Pydantic ==="
uv add pydantic
du -sh .venv/ | awk '{print "Total venv: " $1}'
uv remove pydantic

echo -e "\n=== With cattrs ==="
uv add cattrs
du -sh .venv/ | awk '{print "Total venv: " $1}'
```

---

## Conclusion

For **feedsearch-crawler** as a library package:

1. ✅ **Keep current implementation** - Best for users
2. 🤔 **Consider cattrs** - If automatic serialization is worth +0.5 MB
3. ❌ **Avoid Pydantic** - +10.5 MB is too much overhead for a library

The 162% size increase from Pydantic is difficult to justify for a library that will be installed as a dependency in many projects. The benefits of automatic validation don't outweigh the cost to all downstream users.

If validation is needed, manual `__post_init__` checks (cattrs approach) provide 90% of the benefit at <10% of the cost.
