## Connectors

### Purpose:
Connectors are generally used to Read and/or Write data from/to Sources. For Reads, the output is a dataframe. Conversely, Writes expect a dataframe as the input.
<br><br>

### Implementation:
Sources are file types, repositories, or applications.  
 - For file types, the Connector leverages the underlying pandas read/write APIs.
 - Repositories such as databases require network connection management.
 - Application connectors are built on top of APIs. As such, they need to handle authorization, pagination, etc. Writing to complex, customer-specific objects is best left to custom functions. 
