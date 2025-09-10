# LLM-Client Tests

This directory contains unit tests for the llm-client package components.

## Test Files

### `test_metadata_triage.py`

Tests the metadata triage functionality including:

- Category loading from `categories.v1.json`
- Text redaction (URLs, emails, emojis, whitespace)
- Text truncation (description and tags)
- Tag normalization
- Complete record triage processing

### `test_prompt_builder.py`

Tests the prompt builder functionality including:

- System message generation
- Allowed labels block formatting
- User payload construction
- Complete prompt assembly
- Content with special characters

## Running Tests

### Run all tests:

```bash
cd packages/llm-client/tests
python run_all_tests.py
```

### Run individual test files:

```bash
cd packages/llm-client/tests
python test_metadata_triage.py
python test_prompt_builder.py
```

## Test Coverage

The tests cover:

- ✅ URL and email redaction
- ✅ Emoji and unicode symbol removal
- ✅ Whitespace normalization
- ✅ Text truncation without cutting words
- ✅ Tag processing and normalization
- ✅ JSON category loading
- ✅ Prompt assembly and formatting
- ✅ Edge cases (empty fields, special characters)
- ✅ Error handling and validation

## Adding New Tests

To add new test cases:

1. Add methods starting with `test_` to the appropriate test class
2. The test runner will automatically discover and run them
3. Follow the existing pattern of descriptive test names and assertions
