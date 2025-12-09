# Security Features

LLM Gateway includes built-in security features for protecting sensitive data.

## API Key Encryption

Provider API keys (OpenAI, Anthropic, HuggingFace, etc.) are encrypted at rest using **Fernet symmetric encryption**.

- Keys are encrypted before storage in PostgreSQL
- Decryption happens only at runtime when making LLM calls
- The encryption key is configured via `ENCRYPTION_KEY` environment variable

### Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Configuration

```bash
# .env
ENCRYPTION_KEY=your-fernet-key-here
```

Use different keys for development, staging, and production environments.

## Credential Storage

| Data | Storage | Protection |
|------|---------|------------|
| Provider API keys | PostgreSQL | Fernet encryption |
| Database password | Environment variable | Not stored in code |
| Redis password | Environment variable | Not stored in code |

## Network Security

- API runs on configurable port (default: 8000)
- CORS origins configurable via `CORS_ORIGINS`
- WebSocket connections use same-origin policy
- No authentication built-in (add reverse proxy for auth)

## Recommendations

For production deployments:

- Use a secrets manager (Vault, AWS Secrets Manager) instead of `.env`
- Enable TLS via reverse proxy (nginx, Traefik)
- Restrict database and Redis network access
- Set usage limits on provider API keys
- Monitor API usage for anomalies
