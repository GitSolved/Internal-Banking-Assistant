# Node Store Configuration

Internal Assistant supports multiple node store providers for storing document metadata and index information. The default provider is Simple, but you can configure PostgreSQL for production storage.

## Supported Node Store Providers

Internal Assistant supports the following node store providers:

- **Simple** - Default, in-memory with disk persistence
- **[PostgreSQL](https://www.postgresql.org/)** - Production-ready database storage

## Configuration

To select a node store provider, set the `nodestore.database` property in your `settings.yaml` file:

```yaml
nodestore:
  database: simple  # Options: simple, postgres
```

## Simple Node Store

The Simple node store is the default and recommended choice for most use cases. It provides a combination of in-memory processing and disk persistence.

### Configuration

```yaml
nodestore:
  database: simple
```

### Features

- **In-memory processing** for fast access to frequently used data
- **Disk persistence** to maintain data across application restarts
- **Minimal setup** - no external dependencies required
- **Flexible storage** - suitable for small to medium-sized datasets
- **Data consistency** - maintains consistency across application runs

### Use Cases

The Simple node store is ideal for:

- **Development environments** - Quick setup and testing
- **Small to medium projects** - Efficient data management
- **Proof of concept** - Minimal complexity with full functionality
- **Single-server deployments** - No external database dependencies

### Storage Location

Simple node store data is automatically stored in:

```
local_data/internal_assistant/
├── docstore.json      # Document metadata
├── graph_store.json   # Graph relationships
└── index_store.json   # Index information
```

## PostgreSQL Node Store

PostgreSQL provides a production-ready storage solution with features like transactions, backup, and scalability.

### Installation

First, install the PostgreSQL extra:

```bash
poetry install --extras storage-nodestore-postgres
```

### Configuration

```yaml
nodestore:
  database: postgres

postgres:
  host: localhost
  port: 5432
  database: postgres
  user: postgres
  password: your-password
  schema_name: internal_assistant
```

### Configuration Options

| Field | Description | Default |
|-------|-------------|---------|
| `host` | The server hosting the Postgres database | `localhost` |
| `port` | The port on which the Postgres database is accessible | `5432` |
| `database` | The specific database to connect to | `postgres` |
| `user` | The username for database access | `postgres` |
| `password` | The password for database access | **Required** |
| `schema_name` | The database schema to use | `internal_assistant` |

### Database Schema

When using PostgreSQL, Internal Assistant automatically creates the following tables:

```sql
-- Document metadata table
CREATE TABLE internal_assistant.data_docstore (
    id TEXT PRIMARY KEY,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index information table
CREATE TABLE internal_assistant.data_indexstore (
    id TEXT PRIMARY KEY,
    index_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### PostgreSQL Setup

1. **Install PostgreSQL**:

```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
```

2. **Start PostgreSQL service**:

```bash
# Ubuntu/Debian
sudo systemctl start postgresql

# macOS
brew services start postgresql
```

3. **Create database and user**:

```sql
CREATE DATABASE internal_assistant;
CREATE USER internal_assistant_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE internal_assistant TO internal_assistant_user;
```

4. **Create schema**:

```sql
CREATE SCHEMA internal_assistant;
GRANT ALL ON SCHEMA internal_assistant TO internal_assistant_user;
```

### Verification

After configuration, you can verify the setup by checking the created tables:

```sql
-- Connect to your database
psql -h localhost -U postgres -d internal_assistant

-- List tables in the schema
\dt internal_assistant.*

-- Check table structure
\d internal_assistant.data_docstore
\d internal_assistant.data_indexstore
```

## Performance Considerations

### Simple Node Store

**Advantages:**
- Fast in-memory access
- No external dependencies
- Minimal setup and maintenance
- Suitable for development and small deployments

**Limitations:**
- Limited scalability
- No concurrent access support
- Data stored in JSON files
- No advanced querying capabilities

### PostgreSQL Node Store

**Advantages:**
- Reliable with ACID compliance
- Supports concurrent access
- Advanced querying capabilities
- Built-in backup and recovery
- Scalable for production use

**Limitations:**
- Requires external database setup
- Additional maintenance overhead
- More complex configuration
- Higher resource usage

## Migration Between Node Stores

To migrate from Simple to PostgreSQL (or vice versa):

1. **Backup current data**:
   ```bash
   cp -r local_data/internal_assistant/ backup/
   ```

2. **Update configuration** in `settings.yaml`

3. **Restart the application** - data will be automatically migrated

!!! warning "Data Migration"
    When switching node store providers, ensure you have backups of your data. The migration process may require re-ingesting documents depending on the complexity of your setup.

## Troubleshooting

For node store-specific issues, see the [main troubleshooting guide](../installation/troubleshooting.md#node-store-issues).

### Common Solutions

**Connection Timeout**
```yaml
postgres:
  host: localhost
  port: 5432
  database: internal_assistant
  user: internal_assistant_user
  password: your-password
  schema_name: internal_assistant
  # Add connection pooling if needed
  pool_size: 10
  max_overflow: 20
```

**Memory Issues**
- Increase PostgreSQL shared_buffers
- Optimize work_mem settings
- Consider connection pooling

## Recommendations

### Development Environment
- Use **Simple node store** for quick setup and testing
- Provides all necessary functionality without external dependencies

### Production Environment
- Use **PostgreSQL node store** for reliability and scalability
- Provides better data integrity and concurrent access support

### Hybrid Approach
- Use Simple for development and PostgreSQL for production
- Ensures consistent behavior across environments

## Monitoring

### Simple Node Store Monitoring
- Monitor file sizes in `local_data/internal_assistant/`
- Check disk space usage
- Monitor application memory usage

### PostgreSQL Monitoring
- Monitor database connection count
- Check table sizes and growth
- Monitor query performance
- Set up database backups

For more information on PostgreSQL administration, see the [PostgreSQL Documentation](https://www.postgresql.org/docs/).
