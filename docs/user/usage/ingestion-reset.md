# Reset Local Documents Database

When running in a local setup, you can remove all ingested documents by simply
deleting all contents of `local_data` folder (except .gitignore).

To simplify this process, you can use the command:

```bash
make wipe
```

!!! warning "Data Loss Warning"
    This command will permanently delete all ingested documents and their associated metadata.
    Make sure you have backups if needed before running this command.

## Advanced Usage

You can actually delete your documents from your storage by using the
API endpoint `DELETE` in the Ingestion API.

### Delete All Documents

```bash
curl -X DELETE "http://localhost:8001/v1/ingest" \
  -H "Authorization: Bearer your-api-key"
```

### Delete Specific Document

```bash
curl -X DELETE "http://localhost:8001/v1/ingest/{doc_id}" \
  -H "Authorization: Bearer your-api-key"
```

### Delete Documents by Metadata

You can also delete documents based on specific metadata criteria:

```bash
curl -X DELETE "http://localhost:8001/v1/ingest" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "file_name": "document.pdf",
      "file_type": "pdf",
      "created_after": "2024-01-01T00:00:00Z"
    }
  }'
```

## Manual Reset

If you prefer to manually reset the database:

1. **Stop the application** if it's running
2. **Navigate to the data directory**:
   ```bash
   cd local_data/internal_assistant
   ```
3. **Delete the following files and directories**:
   ```bash
   rm -rf docstore.json
   rm -rf graph_store.json
   rm -rf index_store.json
   rm -rf qdrant/
   rm -rf mitre_attack/
   ```
4. **Restart the application**

!!! note "Preserve Configuration"
    The `make wipe` command preserves your configuration files while removing only the ingested document data.

## Verification

After resetting, you can verify that all documents have been removed:

1. **Check the UI**: Navigate to http://localhost:8001 and verify no documents are listed
2. **Check the API**: Use the status endpoint to confirm empty document count
3. **Check the logs**: Look for confirmation messages in the application logs

## Recovery

If you accidentally deleted documents and need to recover:

1. **Check for backups**: Look for any backup files in your system
2. **Re-ingest documents**: If you have the original files, you can re-ingest them
3. **Check version control**: If documents were committed to git, you can restore them

!!! tip "Prevention"
    Consider setting up regular backups of your `local_data` folder to prevent accidental data loss.
