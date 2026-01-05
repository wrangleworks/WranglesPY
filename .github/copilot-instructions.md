# GitHub Copilot Instructions for WranglesPY

## Project Overview
WranglesPY is a Python package for data wrangling and transformation with AI. It provides modular transformations (Wrangles) for data cleaning, enrichment, extraction, classification, and standardization. The package includes connectors for various data sources and a recipe system for automated workflows.

## General Coding Standards

### Python Style
- Use Python 3 syntax and conventions
- Follow PEP 8 style guidelines
- Use descriptive variable and function names
- Imports should use aliases with underscore prefix (e.g., `import pandas as _pd`, `import json as _json`)
- Use type hints for function parameters (from `typing` module, e.g., `_Union`, `_typing`)
- Group imports: standard library first, then third-party, then local modules

### Code Organization
- Module docstrings should briefly describe the module's purpose
- Function docstrings should include:
  - Brief description of what the function does
  - Example usage (e.g., `'input text' -> 'output'`)
  - `:param` tags for parameters with descriptions
  - `:return:` tag describing the return value
- Use triple double-quotes for docstrings (`"""`)

### Naming Conventions
- Use snake_case for functions and variables
- Use descriptive names that indicate purpose
- Private/internal variables and imports use underscore prefix
- Module-level constants use UPPER_CASE

## Project Structure

### Core Modules
- `wrangles/` - Main package directory
  - `extract.py` - Functions to extract information from text
  - `classify.py` - Classification functions
  - `standardize.py` - Standardization functions
  - `translate.py` - Translation functions
  - `format.py` - Formatting utilities
  - `recipe.py` - Recipe execution engine
  - `auth.py` - Authentication and token management
  - `config.py` - Configuration management
  - `data.py` - Data access functions
  - `connectors/` - Data source connectors (files, databases, APIs)
  - `recipe_wrangles/` - Recipe-specific wrangles

### Connectors
- Located in `wrangles/connectors/`
- Each connector handles read/write operations for a specific data source
- Connectors return DataFrames for read operations and accept DataFrames for write operations
- Handle connection management, authentication, and pagination as needed
- See `wrangles/connectors/README.md` for connector implementation guidelines

### Recipe System
- Recipes are YAML files with `.wrgl.yml` extension
- Recipes define automated sequences of wrangles
- Support for reading data, transforming, and writing to various destinations
- Use templated values with `${}` syntax for variables

## Testing Requirements

### Test Framework
- Use `pytest` for all tests
- Tests are located in the `tests/` directory
- Test files should be named `test_*.py`
- Test functions should be named `test_*`

### Test Structure
- Write focused tests that validate specific functionality
- Use `pytest.raises` for testing error conditions
- Include assertions that validate both the type and value of errors
- Example pattern:
  ```python
  def test_function_error():
      with pytest.raises(ValueError) as info:
          raise function_call(invalid_input)
      assert info.typename == 'ValueError' and info.value.args[0] == 'Expected error message'
  ```

### Test Coverage
- Write tests for both success and error cases
- Test with both single strings and lists of strings for functions that accept both
- Validate error messages and types match expectations

## Authentication and Security

### Credentials Management
- Never hardcode credentials in source code
- Use environment variables for authentication:
  - `WRANGLES_USER` - Username for WrangleWorks API
  - `WRANGLES_PASSWORD` - Password for WrangleWorks API
- Support programmatic authentication via `wrangles.authenticate(user, password)`
- Implement token refresh logic to handle expired access tokens

### API Security
- Use secure token management with expiration checks
- Implement proper error handling for authentication failures
- Use HTTPS for all API communications
- URL-encode credentials when necessary

## Dependencies

### Package Management
- Dependencies are listed in `requirements.txt`
- Core dependencies include:
  - `pandas>=2.0,<3.0` - DataFrame operations
  - `pyyaml` - Recipe parsing
  - `requests` - HTTP requests
  - `sqlalchemy>=2.0,<3.0` - Database connectivity
- Only add new dependencies when absolutely necessary
- Pin major versions for stability

### API Integration
- Use batching for large API requests (see `batching.py`)
- Implement retry logic for network requests (see `utils.request_retries()`)
- Handle rate limiting and pagination appropriately

## Error Handling

### Common Patterns
- Validate input types and raise `TypeError` with descriptive messages
- Validate input values and raise `ValueError` with descriptive messages
- Use `RuntimeError` for authentication and runtime failures
- Always provide clear, actionable error messages
- Example: `'Invalid input data provided. The input must be either a string or a list of strings.'`

### Input Validation
- Check for required parameters and validate format (e.g., model_id format)
- Validate that inputs are correct types (string, list, dict, DataFrame)
- Return appropriate errors when wrong model types are used with functions

## Data Handling

### DataFrame Operations
- Use pandas DataFrames as the primary data structure
- Support both pandas and polars DataFrames where applicable
- Return results in the same format as input (string → string, list → list)
- Handle empty inputs gracefully

### Type Flexibility
- Functions should accept both single strings and lists of strings
- When input is a string, return a single result
- When input is a list, return a list of results in the same order
- Example:
  ```python
  if isinstance(input, str): 
      json_data = [input]
  else:
      json_data = input
  # ... process json_data ...
  if isinstance(input, str): results = results[0]
  return results
  ```

## Performance Considerations
- Use batching for large API calls (see `_batching.batch_api_calls()`)
- Implement concurrent processing where appropriate (see `concurrent.futures`)
- Suppress pandas PerformanceWarnings during recipe execution
- Consider memory efficiency with large datasets

## Documentation
- Keep main documentation at https://wrangles.io/python
- Include docstrings for all public functions
- Provide practical examples in docstrings
- Update README.md for significant feature changes
- Document connector behavior in connector-specific README files

## Recipe Development
- Recipes use YAML format with specific structure (read, wrangles, write)
- Support templated variables with `${}` syntax
- Implement proper variable replacement and validation
- Handle nested recipe structures appropriately
- Support conditional logic with `if` clauses

## Best Practices
- Write clear, maintainable code that follows existing patterns
- Reuse utility functions from `utils.py` for common operations
- Implement proper logging using Python's `logging` module
- Use meaningful commit messages
- Keep functions focused and single-purpose
- Document breaking changes clearly
