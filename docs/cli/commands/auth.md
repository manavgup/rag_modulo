# Authentication Commands

Authentication commands manage user sessions and security tokens for the RAG CLI. All authentication uses IBM OIDC (OpenID Connect) for secure, standards-based authentication.

## Overview

The authentication system provides:
- **IBM OIDC Integration**: Secure authentication flow
- **Token Management**: Automatic refresh and secure storage
- **Multi-Profile Support**: Different credentials per environment
- **Session Management**: Login, logout, and status checking

## Commands Reference

### `rag-cli auth login`

Initiates the IBM OIDC authentication flow.

#### Usage
```bash
./rag-cli auth login [OPTIONS]
```

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--client-id ID` | Override configured client ID | From config |
| `--scope SCOPE` | Override authentication scopes | `openid profile email` |
| `--profile PROFILE` | Use specific profile | `default` |
| `--browser BROWSER` | Specify browser (`chrome`, `firefox`, `safari`) | System default |
| `--no-browser` | Don't open browser automatically | `false` |
| `--timeout SECONDS` | Authentication timeout | `300` |

#### Examples

**Basic authentication:**
```bash
./rag-cli auth login
```

**Custom client ID:**
```bash
./rag-cli auth login --client-id "my-custom-client"
```

**Extended scopes:**
```bash
./rag-cli auth login --scope "openid profile email groups"
```

**Production environment:**
```bash
./rag-cli auth login --profile prod
```

**Manual browser mode:**
```bash
./rag-cli auth login --no-browser
# Opens with: Please visit: https://auth.example.com/oauth/authorize?...
# Then: Enter authorization code:
```

#### Authentication Flow

1. **Initiate Flow**: CLI contacts backend to start OIDC flow
2. **Browser Opens**: Default browser opens to IBM OIDC provider
3. **User Authentication**: User logs in with IBM credentials
4. **Authorization Code**: User copies code from redirect URL
5. **Token Exchange**: CLI exchanges code for JWT token
6. **Token Storage**: Token stored securely in `~/.rag/tokens/`

#### Expected Output

**Successful authentication:**
```
🌐 Opening browser for authentication...
✅ Authentication successful!

User: john.doe@company.com
Expires: 2024-01-15 14:30:00 UTC
Profile: default

You can now use other CLI commands.
```

**Manual browser mode:**
```
Please visit the following URL to authenticate:
https://auth.example.com/oauth/authorize?client_id=...

After authentication, you'll be redirected to a URL with a 'code' parameter.
Enter the authorization code: abc123def456

✅ Authentication successful!
```

---

### `rag-cli auth status`

Check current authentication status and user information.

#### Usage
```bash
./rag-cli auth status [OPTIONS]
```

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--profile PROFILE` | Check specific profile | Current active |
| `--verbose` | Show detailed token information | `false` |
| `--quiet` | Only return exit code (0=auth, 1=not auth) | `false` |

#### Examples

**Basic status check:**
```bash
./rag-cli auth status
```

**Check specific profile:**
```bash
./rag-cli auth status --profile prod
```

**Detailed information:**
```bash
./rag-cli auth status --verbose
```

**Silent check for scripting:**
```bash
if ./rag-cli auth status --quiet; then
    echo "Authenticated"
fi
```

#### Output Examples

**Authenticated user:**
```
✅ Authenticated

User: john.doe@company.com
Email: john.doe@company.com
Expires: 2024-01-15 14:30:00 UTC (in 2 hours)
Profile: default
Scopes: openid, profile, email
```

**Not authenticated:**
```
❌ Not authenticated

Run 'rag-cli auth login' to authenticate.
```

**Verbose output:**
```
✅ Authenticated

User Information:
  ID: john.doe@company.com
  Email: john.doe@company.com
  Name: John Doe
  Groups: developers, rag-users

Token Information:
  Type: Bearer
  Expires: 2024-01-15 14:30:00 UTC (in 2 hours)
  Issued: 2024-01-15 12:30:00 UTC
  Scopes: openid, profile, email

Profile: default
Backend: http://localhost:8000
```

---

### `rag-cli auth logout`

Log out and clear stored authentication tokens.

#### Usage
```bash
./rag-cli auth logout [OPTIONS]
```

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--profile PROFILE` | Logout specific profile | Current active |
| `--all` | Logout all profiles | `false` |
| `--clear-config` | Also clear authentication configuration | `false` |

#### Examples

**Basic logout:**
```bash
./rag-cli auth logout
```

**Logout specific profile:**
```bash
./rag-cli auth logout --profile prod
```

**Logout all profiles:**
```bash
./rag-cli auth logout --all
```

**Complete cleanup:**
```bash
./rag-cli auth logout --clear-config
```

#### Expected Output

**Successful logout:**
```
✅ Logged out successfully

Profile: default
Tokens cleared from local storage.
```

**Logout all profiles:**
```
✅ Logged out from all profiles

Profiles cleared: default, prod, staging
All tokens cleared from local storage.
```

---

### `rag-cli auth refresh`

Manually refresh authentication token.

#### Usage
```bash
./rag-cli auth refresh [OPTIONS]
```

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--profile PROFILE` | Refresh specific profile | Current active |
| `--force` | Force refresh even if not expired | `false` |

#### Examples

**Basic refresh:**
```bash
./rag-cli auth refresh
```

**Force refresh:**
```bash
./rag-cli auth refresh --force
```

**Refresh specific profile:**
```bash
./rag-cli auth refresh --profile prod
```

#### Expected Output

**Successful refresh:**
```
✅ Token refreshed successfully

New expiration: 2024-01-15 16:30:00 UTC (in 4 hours)
```

**No refresh needed:**
```
ℹ️ Token still valid for 3 hours, no refresh needed.

Use --force to refresh anyway.
```

**Refresh failed:**
```
❌ Token refresh failed

The refresh token may be expired. Please re-authenticate:
./rag-cli auth login
```

---

### `rag-cli auth whoami`

Display detailed current user information.

#### Usage
```bash
./rag-cli auth whoami [OPTIONS]
```

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--profile PROFILE` | Check specific profile | Current active |
| `--verbose` | Show detailed user information | `false` |
| `--format FORMAT` | Output format (`table`, `json`, `yaml`) | `table` |

#### Examples

**Basic user info:**
```bash
./rag-cli auth whoami
```

**Detailed information:**
```bash
./rag-cli auth whoami --verbose
```

**JSON output:**
```bash
./rag-cli auth whoami --format json
```

#### Expected Output

**Basic output:**
```
👤 Current User

Name: John Doe
Email: john.doe@company.com
ID: john.doe@company.com
Profile: default
```

**Verbose output:**
```
👤 Current User

Personal Information:
  Name: John Doe
  Email: john.doe@company.com
  ID: john.doe@company.com

Authorization:
  Groups: developers, rag-users, admin
  Scopes: openid, profile, email, groups
  Permissions: read, write, admin

Session Information:
  Authenticated: 2024-01-15 12:30:00 UTC
  Expires: 2024-01-15 14:30:00 UTC (in 2 hours)
  Profile: default
  Backend: http://localhost:8000
```

**JSON output:**
```json
{
  "user": {
    "id": "john.doe@company.com",
    "email": "john.doe@company.com",
    "name": "John Doe",
    "groups": ["developers", "rag-users", "admin"]
  },
  "session": {
    "authenticated_at": "2024-01-15T12:30:00Z",
    "expires_at": "2024-01-15T14:30:00Z",
    "scopes": ["openid", "profile", "email", "groups"],
    "profile": "default"
  },
  "backend": {
    "url": "http://localhost:8000",
    "authenticated": true
  }
}
```

## Error Handling

### Common Error Scenarios

#### Authentication Required
```bash
$ ./rag-cli auth status
❌ Not authenticated

Run 'rag-cli auth login' to authenticate.
```

#### Expired Token
```bash
$ ./rag-cli auth status
⚠️ Token expired

Your authentication token expired 30 minutes ago.
Run 'rag-cli auth login' to re-authenticate.
```

#### Network Connectivity Issues
```bash
$ ./rag-cli auth login
❌ Authentication failed

Unable to connect to authentication server.
- Check network connectivity
- Verify backend URL: http://localhost:8000
- Check firewall settings
```

#### Invalid Credentials
```bash
$ ./rag-cli auth login
❌ Authentication failed

Invalid client credentials or configuration.
- Verify client ID: your-client-id
- Check OIDC provider configuration
- Contact administrator for valid credentials
```

### Debug Mode

Enable debug logging for authentication troubleshooting:

```bash
# Enable debug for single command
./rag-cli --debug auth login

# Enable debug globally
./rag-cli config set debug true
./rag-cli auth login
```

Debug output includes:
- HTTP requests and responses
- Token parsing details
- Configuration values used
- Timing information

## Configuration Integration

Authentication commands respect CLI configuration:

### Profile-Specific Settings
```bash
# Set client ID for profile
./rag-cli config set auth.client_id "prod-client" --profile prod

# Set custom OIDC issuer
./rag-cli config set auth.issuer "https://auth.company.com" --profile prod

# View auth configuration
./rag-cli config show auth --profile prod
```

### Global Authentication Settings
```bash
# Set default scopes
./rag-cli config set auth.default_scope "openid profile email groups"

# Set token refresh buffer (seconds before expiry)
./rag-cli config set auth.refresh_buffer 300

# Enable automatic token refresh
./rag-cli config set auth.auto_refresh true
```

## Scripting Examples

### Check Authentication in Scripts
```bash
#!/bin/bash

# Function to ensure authentication
ensure_authenticated() {
    if ! ./rag-cli auth status --quiet; then
        echo "Authentication required. Please log in:"
        ./rag-cli auth login

        if ! ./rag-cli auth status --quiet; then
            echo "Authentication failed. Exiting."
            exit 1
        fi
    fi
}

# Use in script
ensure_authenticated
./rag-cli collections list
```

### Multi-Environment Authentication
```bash
#!/bin/bash

# Authenticate against different environments
environments=("dev" "staging" "prod")

for env in "${environments[@]}"; do
    echo "Authenticating against $env..."
    ./rag-cli auth login --profile $env

    if ./rag-cli auth status --profile $env --quiet; then
        echo "✅ $env authentication successful"
    else
        echo "❌ $env authentication failed"
    fi
done
```

### Token Information Extraction
```bash
#!/bin/bash

# Get token expiration time
expiry=$(./rag-cli auth whoami --format json | jq -r '.session.expires_at')

# Check if token expires soon (within 1 hour)
current_time=$(date -u +%s)
expiry_time=$(date -d "$expiry" +%s)
time_diff=$((expiry_time - current_time))

if [ $time_diff -lt 3600 ]; then
    echo "Token expires soon, refreshing..."
    ./rag-cli auth refresh
fi
```

## Security Considerations

### Token Storage
- Tokens stored in `~/.rag/tokens/` with 600 permissions
- Files are readable only by the user
- Tokens are encrypted at rest (when possible)

### Best Practices
1. **Regular Rotation**: Re-authenticate periodically
2. **Environment Separation**: Use different profiles for different environments
3. **Secure Networks**: Authenticate only on trusted networks
4. **Audit Logging**: Monitor authentication events
5. **Token Expiration**: Use reasonable token lifetimes

### Troubleshooting Security Issues
```bash
# Check token file permissions
ls -la ~/.rag/tokens/

# Reset token storage if compromised
rm -rf ~/.rag/tokens/
./rag-cli auth login

# Verify token integrity
./rag-cli auth status --verbose
```

## Next Steps

After mastering authentication:
1. **[Collections](collections.md)** - Create and manage document collections
2. **[Documents](documents.md)** - Upload and process documents
3. **[Search](search.md)** - Perform queries and searches
4. **[Configuration](../configuration.md)** - Advanced authentication configuration
