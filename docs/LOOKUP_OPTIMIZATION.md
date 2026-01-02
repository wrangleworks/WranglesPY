# Lookup Functionality and Optimization

## Overview

Lookups in Wrangles allow you to enrich data by retrieving information from saved lookup models. This document explains how the lookup functionality works and describes the optimization for scenarios where all rows need the same lookup value.

## How Lookups Work

### Architecture

The lookup functionality consists of three main components:

1. **`wrangles.lookup()`** - Direct function API
   - Accepts a single value or list of values
   - Returns lookup results from a specified model
   - Can return specific columns or all columns as a dictionary

2. **`wrangles.recipe_wrangles.main.lookup()`** - Recipe wrangle implementation
   - Applies lookup operations to DataFrame columns
   - Processes entire columns at once
   - Integrates with the recipe execution pipeline

3. **`wrangles.batching.batch_api_calls()`** - API request handler
   - Batches large requests into manageable chunks
   - Handles authentication and retries
   - Combines results from multiple batches

### Lookup Flow

```
DataFrame Column → Extract Values → Batch API Calls → Process Results → Update DataFrame
```

#### Detailed Steps:

1. **Input Extraction**: Values from the specified input column are extracted
2. **Validation**: Model ID is validated and metadata is retrieved
3. **API Request**: Values are sent to the lookup API in batches
4. **Result Processing**: API responses are formatted based on requested columns
5. **DataFrame Update**: Results are assigned back to the output column(s)

### Usage Examples

#### Direct Function API

```python
import wrangles

# Single value lookup
result = wrangles.lookup("input_value", "12345678-1234-1234")
# Returns: {'column1': 'value1', 'column2': 'value2'}

# Single column from lookup
result = wrangles.lookup("input_value", "12345678-1234-1234", columns="column1")
# Returns: 'value1'

# Multiple values
result = wrangles.lookup(["val1", "val2", "val3"], "12345678-1234-1234")
# Returns: [{'column1': 'a', ...}, {'column1': 'b', ...}, {'column1': 'c', ...}]
```

#### Recipe Usage

```yaml
read:
  - file:
      name: input.csv

wrangles:
  - lookup:
      input: product_code
      output: product_name
      model_id: 12345678-1234-1234

write:
  - file:
      name: output.csv
```

## Optimization for Constant Values

### Problem

When all rows in a DataFrame contain the same value in the lookup input column, the original implementation would:
- Send that same value N times to the API (where N = number of rows)
- Waste API bandwidth and processing time
- Increase latency proportionally to the number of rows

### Solution

An optimization has been implemented that detects when all values in the input column are identical:

```python
# Check if all values are the same
unique_values = df[input].unique()
if len(unique_values) == 1:
    # Perform lookup only once
    single_result = lookup(unique_values[0], model_id, ...)
    # Broadcast result to all rows
    df[output] = [single_result] * num_rows
```

### Benefits

1. **Performance**: Reduces API calls from N to 1 when all values are identical
2. **Efficiency**: Minimizes network bandwidth usage
3. **Cost**: Potentially reduces API usage costs
4. **Backward Compatible**: Standard behavior maintained for variable values

### When Optimization Applies

The optimization is triggered when:
- All rows in the input column contain exactly the same value
- The DataFrame is not empty

The standard path is used when:
- Rows contain different values
- Multiple unique values exist in the input column

### Performance Comparison

| Scenario | Rows | Unique Values | API Calls (Before) | API Calls (After) | Improvement |
|----------|------|---------------|-------------------|-------------------|-------------|
| Constant | 1,000 | 1 | 1,000 | 1 | 99.9% reduction |
| Constant | 10,000 | 1 | 10,000 | 1 | 99.99% reduction |
| Variable | 1,000 | 1,000 | 1,000 | 1,000 | No change |
| Mixed | 1,000 | 100 | 1,000 | 1,000 | No change |

*Note: Actual API calls may be divided into batches based on the model's batch size configuration*

### Implementation Details

The optimization:
- Detects constant values using `df[input].unique()`
- Makes a single lookup call with the constant value
- Broadcasts the result to all rows using list multiplication
- Handles all output formats: single column, multiple columns, and dictionary outputs
- Preserves exact behavior for non-constant scenarios

### Testing

Comprehensive tests ensure:
- Optimization works correctly for single column outputs
- Optimization works correctly for multiple column outputs
- Optimization works correctly for dictionary outputs
- Standard path continues to work for variable values
- Empty DataFrames are handled properly

See `tests/test_lookup_optimization.py` for implementation details.

## Future Enhancements

Potential improvements could include:
1. **Partial Optimization**: Lookup only unique values and map results back
2. **Caching**: Cache recent lookup results within a recipe execution
3. **Bulk Optimization**: Identify groups of identical values across multiple columns
4. **Metrics**: Track and report optimization savings

## Technical Notes

### Thread Safety

The optimization uses pandas DataFrame operations which are not inherently thread-safe. When using lookups in multi-threaded environments, ensure proper synchronization.

### Memory Considerations

Broadcasting results uses list multiplication (`[result] * n`), which creates a list with n references to the same object. This is memory-efficient as it doesn't duplicate the actual data.

### API Batching

The optimization works at the recipe wrangle level before batching occurs. When standard lookup is used with many unique values, the batching mechanism still applies to prevent overwhelming the API.
