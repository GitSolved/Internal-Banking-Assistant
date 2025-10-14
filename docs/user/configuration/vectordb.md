# Vector Database Configuration

Internal Assistant supports multiple vector database providers for storing and retrieving document embeddings. The default provider is Qdrant, but you can configure others based on your needs.

## Supported Vector Databases

Internal Assistant supports the following vector database providers:

- **[Qdrant](https://qdrant.tech/)** - Default vector database
- **[Milvus](https://milvus.io/)** - Scalable vector database for production
- **[Chroma](https://www.trychroma.com/)** - Open-source embedding database
- **[PGVector](https://github.com/pgvector/pgvector)** - PostgreSQL extension for vector operations
- **[ClickHouse](https://github.com/ClickHouse/ClickHouse)** - Analytical database

## Configuration

To select a vector database provider, set the `vectorstore.database` property in your `settings.yaml` file:

```yaml
vectorstore:
  database: qdrant  # Options: qdrant, milvus, chroma, postgres, clickhouse
```

## Qdrant Configuration

Qdrant is the default and recommended vector database for Internal Assistant.

### Basic Configuration

```yaml
vectorstore:
  database: qdrant

qdrant:
  path: local_data/internal_assistant/qdrant
```

### Advanced Configuration Options

| Field | Description | Default |
|-------|-------------|---------|
| `location` | If `:memory:` - use in-memory Qdrant instance. If `str` - use it as a `url` parameter | `local_data/internal_assistant/qdrant` |
| `url` | Either host or str of 'Optional[scheme], host, Optional[port], Optional[prefix]'. Eg. `http://localhost:6333` | `http://localhost:6333` |
| `port` | Port of the REST API interface | `6333` |
| `grpc_port` | Port of the gRPC interface | `6334` |
| `prefer_grpc` | If `true` - use gRPC interface whenever possible in custom methods | `false` |
| `https` | If `true` - use HTTPS(SSL) protocol | `false` |
| `api_key` | API key for authentication in Qdrant Cloud | - |
| `prefix` | If set, add `prefix` to the REST URL path. Example: `service/v1` | - |
| `timeout` | Timeout for REST and gRPC API requests | `5.0` seconds for REST, unlimited for gRPC |
| `host` | Host name of Qdrant service | `localhost` |
| `path` | Persistence path for QdrantLocal | `local_data/internal_assistant/qdrant` |
| `force_disable_check_same_thread` | Force disable check_same_thread for QdrantLocal sqlite connection | `true` |

### Local Setup (Recommended)

For local development, use the disk-based database without running a separate Qdrant server:

```yaml
vectorstore:
  database: qdrant

qdrant:
  path: local_data/internal_assistant/qdrant
```

### Remote Qdrant Server

To connect to a remote Qdrant server:

```yaml
vectorstore:
  database: qdrant

qdrant:
  url: http://your-qdrant-server:6333
  api_key: your-api-key  # If using Qdrant Cloud
```

## Milvus Configuration

Milvus is a scalable vector database suitable for production environments.

### Installation

First, install the Milvus extra:

```bash
poetry install --extras vector-stores-milvus
```

### Configuration

```yaml
vectorstore:
  database: milvus

milvus:
  uri: local_data/internal_assistant/milvus/milvus_local.db
  collection_name: milvus_db
  overwrite: true
```

### Configuration Options

| Field | Description | Default |
|-------|-------------|---------|
| `uri` | Database URI. For local setup: `local_data/internal_assistant/milvus/milvus_local.db`. For remote: `http://localhost:19530` | `local_data/internal_assistant/milvus/milvus_local.db` |
| `token` | API key for Zilliz Cloud or authentication token | - |
| `collection_name` | The name of the collection | `milvus_db` |
| `overwrite` | Overwrite the data in collection if it existed | `true` |

### Remote Milvus Setup

For production, connect to a remote Milvus server:

```yaml
vectorstore:
  database: milvus

milvus:
  uri: http://your-milvus-server:19530
  token: your-api-key
  collection_name: internal_assistant_docs
```

## Chroma Configuration

Chroma is an open-source embedding database with a simple setup.

### Installation

```bash
poetry install --extras chroma
```

### Configuration

```yaml
vectorstore:
  database: chroma

# Chroma will automatically use local_data_path/chroma_db
```

Chroma automatically stores data in `local_data_path/chroma_db` where `local_data_path` is defined in your settings.

## PGVector Configuration

PGVector is a PostgreSQL extension that adds vector operations to PostgreSQL.

### Installation

```bash
poetry install --extras vector-stores-postgres
```

### Configuration

```yaml
vectorstore:
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

### PostgreSQL Setup

1. **Install PostgreSQL** and the PGVector extension:

```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo apt-get install postgresql-14-pgvector  # Adjust version as needed

# macOS
brew install postgresql
brew install pgvector
```

2. **Enable the extension** in your PostgreSQL database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

3. **Create the database and user**:

```sql
CREATE DATABASE internal_assistant;
CREATE USER internal_assistant_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE internal_assistant TO internal_assistant_user;
```

## ClickHouse Configuration

ClickHouse is an analytical database with vector support.

### Installation

```bash
poetry install --extras vector-stores-clickhouse
```

### Configuration

```yaml
vectorstore:
  database: clickhouse

clickhouse:
  host: localhost
  port: 8123
  database: default
  user: default
  password: ""
  secure: false
```

## Performance Considerations

### Memory Usage

- **Qdrant (Local)**: Low memory usage, suitable for development
- **Milvus**: Higher memory usage, better for production workloads
- **Chroma**: Moderate memory usage, good for small to medium datasets
- **PGVector**: Depends on PostgreSQL configuration
- **ClickHouse**: High performance, requires more resources

### Scalability

- **Qdrant**: Good for small to medium datasets
- **Milvus**: Excellent for large-scale production deployments
- **Chroma**: Good for development and small production deployments
- **PGVector**: Scales with PostgreSQL capabilities
- **ClickHouse**: Excellent for large-scale analytics

### Recommendations

- **Development**: Use Qdrant local setup
- **Small Production**: Use Qdrant or Chroma
- **Large Production**: Use Milvus or ClickHouse
- **Existing PostgreSQL**: Use PGVector

## Migration Between Vector Databases

To migrate from one vector database to another:

1. **Export data** from current database
2. **Update configuration** in `settings.yaml`
3. **Re-ingest documents** to populate new database

!!! warning "Data Migration"
    Vector database migrations require re-ingesting all documents, as embeddings are stored in database-specific formats.

## Troubleshooting

For vector database-specific issues, see the [main troubleshooting guide](../installation/troubleshooting.md#vector-database-issues).

### Getting Help

For vector database-specific documentation:

- **Qdrant**: [Qdrant Documentation](https://qdrant.tech/documentation/)
- **Milvus**: [Milvus Documentation](https://milvus.io/docs)
- **Chroma**: [Chroma Documentation](https://docs.trychroma.com/)
- **PGVector**: [PGVector Documentation](https://github.com/pgvector/pgvector)
- **ClickHouse**: [ClickHouse Documentation](https://clickhouse.com/docs)
