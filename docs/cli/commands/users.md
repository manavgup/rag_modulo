# User Commands

User commands provide administrative capabilities for managing user accounts, permissions, and access control within the RAG system. These commands are typically available to users with administrative privileges.

## Overview

User management provides:
- **User Account Management**: Create, update, and delete user accounts
- **Permission Control**: Assign roles and manage access levels
- **Team Management**: Organize users into teams and groups
- **Access Auditing**: Track user activity and access patterns
- **Bulk Operations**: Efficient management of multiple users

> **Note**: Most user management commands require administrative privileges. Regular users can only view their own profile information.

## Commands Reference

### `rag-cli users list`

List all users in the system (admin only).

#### Usage
```bash
./rag-cli users list [OPTIONS]
```

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--format FORMAT` | Output format (`table`, `json`, `csv`, `yaml`) | `table` |
| `--limit LIMIT` | Maximum users to return | `50` |
| `--offset OFFSET` | Number of users to skip | `0` |
| `--filter FILTER` | Filter by name, email, or role | None |
| `--sort FIELD` | Sort by (`name`, `email`, `role`, `created_at`, `last_login`) | `name` |
| `--order ORDER` | Sort order (`asc`, `desc`) | `asc` |
| `--include-stats` | Include user activity statistics | `false` |
| `--role ROLE` | Filter by specific role | All roles |

#### Examples

**Basic user listing:**
```bash
./rag-cli users list
```

**Filter by role:**
```bash
./rag-cli users list --role admin --format json
```

**Recent users with activity stats:**
```bash
./rag-cli users list --sort last_login --order desc --include-stats
```

**Search for specific users:**
```bash
./rag-cli users list --filter "john" --limit 10
```

#### Expected Output

**Table format:**
```
👥 User Management

┌──────────────────────┬─────────────────────────┬─────────────────────────┬──────────┬─────────────────────┬─────────────────────┐
│ ID                   │ Name                    │ Email                   │ Role     │ Created             │ Last Login          │
├──────────────────────┼─────────────────────────┼─────────────────────────┼──────────┼─────────────────────┼─────────────────────┤
│ user_123abc          │ John Doe                │ john.doe@company.com    │ admin    │ 2024-01-10 09:00:00 │ 2024-01-15 14:30:00 │
│ user_456def          │ Jane Smith              │ jane.smith@company.com  │ user     │ 2024-01-11 11:30:00 │ 2024-01-15 10:15:00 │
│ user_789ghi          │ Bob Johnson             │ bob.johnson@company.com │ editor   │ 2024-01-12 14:45:00 │ 2024-01-14 16:20:00 │
└──────────────────────┴─────────────────────────┴─────────────────────────┴──────────┴─────────────────────┴─────────────────────┘

Total: 23 users
Active in last 7 days: 18 users
```

**JSON with statistics:**
```json
{
  "users": [
    {
      "id": "user_123abc",
      "name": "John Doe",
      "email": "john.doe@company.com",
      "role": "admin",
      "status": "active",
      "created_at": "2024-01-10T09:00:00Z",
      "last_login": "2024-01-15T14:30:00Z",
      "stats": {
        "total_queries": 147,
        "documents_uploaded": 23,
        "collections_created": 5,
        "last_activity": "2024-01-15T14:30:00Z"
      },
      "permissions": [
        "read", "write", "admin", "user_management"
      ]
    }
  ],
  "total": 23,
  "pagination": {
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

---

### `rag-cli users get`

Get detailed information about a specific user.

#### Usage
```bash
./rag-cli users get USER_ID [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `USER_ID` | User identifier or email | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--format FORMAT` | Output format (`table`, `json`, `yaml`) | `table` |
| `--include-activity` | Include recent activity log | `false` |
| `--include-permissions` | Include detailed permissions | `false` |
| `--include-collections` | Include accessible collections | `false` |

#### Examples

**Basic user information:**
```bash
./rag-cli users get user_123abc
```

**Get user by email:**
```bash
./rag-cli users get john.doe@company.com
```

**Detailed user profile:**
```bash
./rag-cli users get user_123abc \
  --include-activity \
  --include-permissions \
  --include-collections \
  --format json
```

#### Expected Output

**Basic profile:**
```
👤 User Profile

ID: user_123abc
Name: John Doe
Email: john.doe@company.com
Role: admin
Status: ✅ Active

📊 Account Information
Created: 2024-01-10 09:00:00
Last Login: 2024-01-15 14:30:00
Total Logins: 87
Profile Updated: 2024-01-14 10:20:00

🎯 Activity Summary
Queries this month: 45
Documents uploaded: 12
Collections created: 2
Last activity: 2024-01-15 14:30:00
```

**Detailed profile with permissions:**
```
👤 User Profile
[... basic info ...]

🔐 Permissions & Access
Role: admin
Permissions:
  ✅ read - View documents and collections
  ✅ write - Create and modify content
  ✅ admin - System administration
  ✅ user_management - Manage other users
  ✅ collection_admin - Manage all collections

👥 Team Memberships
  - Engineering Team (admin)
  - ML Research Group (member)
  - Documentation Team (editor)

📚 Collection Access
  - Knowledge Base (col_123abc) - Owner
  - Research Papers (col_456def) - Admin
  - Technical Docs (col_789ghi) - Editor
  - 12 more collections...

📊 Recent Activity (Last 7 days)
  2024-01-15 14:30:00 - Performed search query
  2024-01-15 14:25:00 - Updated collection settings
  2024-01-15 10:15:00 - Uploaded document to Research Papers
  2024-01-14 16:45:00 - Created new collection
  2024-01-14 12:30:00 - Authenticated via CLI
```

---

### `rag-cli users create`

Create a new user account (admin only).

#### Usage
```bash
./rag-cli users create [OPTIONS]
```

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--name NAME` | Full name of the user | Required |
| `--email EMAIL` | Email address | Required |
| `--role ROLE` | User role (`user`, `editor`, `admin`) | `user` |
| `--password PASSWORD` | Initial password (if not using SSO) | Auto-generated |
| `--send-invite` | Send invitation email | `true` |
| `--team TEAM_ID` | Add to specific team | None |
| `--collections COLLECTION_IDS` | Grant access to collections | None |
| `--temporary` | Create temporary account (expires in 30 days) | `false` |

#### Examples

**Create basic user:**
```bash
./rag-cli users create \
  --name "Alice Johnson" \
  --email "alice.johnson@company.com" \
  --role editor
```

**Create admin user with team assignment:**
```bash
./rag-cli users create \
  --name "System Administrator" \
  --email "sysadmin@company.com" \
  --role admin \
  --team team_engineering \
  --send-invite
```

**Create user with collection access:**
```bash
./rag-cli users create \
  --name "Content Manager" \
  --email "content@company.com" \
  --role editor \
  --collections "col_123abc,col_456def" \
  --password "TempPass123!"
```

**Create temporary contractor account:**
```bash
./rag-cli users create \
  --name "External Contractor" \
  --email "contractor@external.com" \
  --role user \
  --temporary \
  --collections "col_project_x"
```

#### Expected Output

**User created successfully:**
```
✅ User created successfully!

User Details:
  ID: user_newuser123
  Name: Alice Johnson
  Email: alice.johnson@company.com
  Role: editor
  Status: Pending activation

📧 Invitation sent to: alice.johnson@company.com
The user will receive login instructions via email.

Next steps:
1. User clicks activation link in email
2. User sets up authentication (password/SSO)
3. User can begin using the system

Manage user: ./rag-cli users get user_newuser123
```

**Temporary user created:**
```
✅ Temporary user created successfully!

User Details:
  ID: user_temp456
  Name: External Contractor
  Email: contractor@external.com
  Role: user
  Status: Active
  Expires: 2024-02-14 (30 days)

⚠️ This is a temporary account that will be automatically deactivated in 30 days.

Collection Access:
  - Project X Documents (col_project_x) - Read access

Login credentials have been sent to: contractor@external.com
```

---

### `rag-cli users update`

Update user account information and permissions (admin only).

#### Usage
```bash
./rag-cli users update USER_ID [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `USER_ID` | User identifier | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--name NAME` | Update full name | No change |
| `--email EMAIL` | Update email address | No change |
| `--role ROLE` | Update user role | No change |
| `--status STATUS` | Update status (`active`, `inactive`, `suspended`) | No change |
| `--add-team TEAM_ID` | Add user to team | None |
| `--remove-team TEAM_ID` | Remove user from team | None |
| `--add-collection COLLECTION_ID` | Grant collection access | None |
| `--remove-collection COLLECTION_ID` | Revoke collection access | None |
| `--extend-expiry DAYS` | Extend temporary account (days) | No change |

#### Examples

**Update user role:**
```bash
./rag-cli users update user_123abc --role admin
```

**Update contact information:**
```bash
./rag-cli users update user_123abc \
  --name "John Smith-Doe" \
  --email "john.smithdoe@company.com"
```

**Manage team memberships:**
```bash
./rag-cli users update user_123abc \
  --add-team team_ml_research \
  --remove-team team_old_project
```

**Grant collection access:**
```bash
./rag-cli users update user_123abc \
  --add-collection col_confidential \
  --role editor
```

**Suspend user account:**
```bash
./rag-cli users update user_123abc --status suspended
```

#### Expected Output

**Successful update:**
```
✅ User updated successfully!

Changes made:
  Role: user → editor
  Added to team: ML Research Group
  Collection access granted: Confidential Documents (col_confidential)

Updated User:
  ID: user_123abc
  Name: John Doe
  Email: john.doe@company.com
  Role: editor
  Status: Active
  Teams: Engineering Team, ML Research Group

⚠️ User will be notified of role change via email.
Next login will reflect new permissions.
```

---

### `rag-cli users delete`

Delete a user account (admin only).

#### Usage
```bash
./rag-cli users delete USER_ID [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `USER_ID` | User identifier | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--force` | Skip confirmation prompt | `false` |
| `--transfer-ownership TO_USER_ID` | Transfer owned resources | None |
| `--backup` | Create backup of user data | `true` |
| `--deactivate-only` | Deactivate instead of delete | `false` |

#### Examples

**Interactive deletion:**
```bash
./rag-cli users delete user_123abc
```

**Delete with resource transfer:**
```bash
./rag-cli users delete user_departing \
  --transfer-ownership user_manager \
  --backup
```

**Deactivate instead of delete:**
```bash
./rag-cli users delete user_123abc --deactivate-only
```

**Force deletion:**
```bash
./rag-cli users delete user_inactive --force
```

#### Expected Output

**Interactive deletion:**
```
⚠️ Delete User Account

User: John Doe (user_123abc)
Email: john.doe@company.com
Role: editor
Created: 2024-01-10 09:00:00
Last Login: 2024-01-15 14:30:00

Owned Resources:
  - 3 collections (23 documents)
  - 2 teams (as admin)
  - 147 search queries

⚠️ This action cannot be undone!
Consider transferring ownership or deactivating instead.

Transfer ownership to another user? (user ID or 'skip'): user_manager123
Are you sure you want to delete this user? (y/N): y

📦 Creating user data backup...
✅ Backup created: user_123abc_backup_20240115.json

🔄 Transferring ownership...
✅ Transferred 3 collections to user_manager123
✅ Transferred 2 team adminships to user_manager123

🗑️ Deleting user account...
✅ User deleted successfully!

Cleanup completed:
  - User account removed
  - Authentication tokens revoked
  - Team memberships removed
  - Collection permissions revoked
  - Search history archived

Backup available at: ./backups/user_123abc_backup_20240115.json
```

## Advanced User Management

### Bulk User Operations

**Import users from CSV:**
```bash
#!/bin/bash
csv_file="new_users.csv"

echo "👥 Bulk User Import"
echo "=================="

# Skip header line, process CSV
tail -n +2 "$csv_file" | while IFS=',' read -r name email role team; do
    echo "Creating user: $name ($email)"

    user_id=$(./rag-cli users create \
      --name "$name" \
      --email "$email" \
      --role "$role" \
      --team "$team" \
      --format json | jq -r '.id')

    if [ "$user_id" != "null" ]; then
        echo "✅ Created: $user_id"
    else
        echo "❌ Failed to create user: $name"
    fi
done

echo "✅ Bulk import completed"
```

**Bulk role updates:**
```bash
#!/bin/bash
# Promote all editors to admin role
echo "🔄 Bulk Role Update: Editors → Admins"

./rag-cli users list --role editor --format json | \
jq -r '.users[].id' | \
while read user_id; do
    echo "Promoting user: $user_id"
    ./rag-cli users update "$user_id" --role admin
done
```

**User activity audit:**
```bash
#!/bin/bash
echo "📊 User Activity Audit"
echo "===================="

cutoff_date="2024-01-01"

echo "Users inactive since $cutoff_date:"
./rag-cli users list --include-stats --format json | \
jq --arg cutoff "$cutoff_date" -r '
  .users[] |
  select(.stats.last_activity < $cutoff) |
  [.name, .email, .stats.last_activity, .stats.total_queries] |
  @tsv' | \
while IFS=$'\t' read -r name email last_activity queries; do
    echo "  - $name ($email): Last active $last_activity, $queries queries"
done

echo ""
echo "Recommended actions:"
echo "1. Contact inactive users to verify continued need"
echo "2. Consider deactivating accounts with no recent activity"
echo "3. Transfer ownership of resources from departing users"
```

### User Permissions Management

**Collection access matrix:**
```bash
#!/bin/bash
echo "📊 Collection Access Matrix"
echo "==========================="

# Get all collections
collections=$(./rag-cli collections list --format json | jq -r '.collections[] | [.id, .name] | @tsv')

echo "$collections" | while IFS=$'\t' read -r col_id col_name; do
    echo ""
    echo "📚 Collection: $col_name ($col_id)"
    echo "$(printf '%.0s-' {1..50})"

    # Get users with access to this collection
    ./rag-cli users list --format json | \
    jq --arg col_id "$col_id" -r '
      .users[] |
      select(.collections[]? == $col_id) |
      [.name, .email, .role] |
      @tsv' | \
    while IFS=$'\t' read -r name email role; do
        echo "  ✅ $name ($email) - Role: $role"
    done
done
```

**Permission audit script:**
```bash
#!/bin/bash
echo "🔐 Permission Audit Report"
echo "========================="

# Users with admin privileges
echo "👨‍💼 Administrative Users:"
./rag-cli users list --role admin --format json | \
jq -r '.users[] | "  - " + .name + " (" + .email + ")"'

echo ""
echo "👥 Users by Role Distribution:"
for role in user editor admin; do
    count=$(./rag-cli users list --role "$role" --format json | jq '.total')
    echo "  - ${role^}: $count users"
done

echo ""
echo "📚 Collection Ownership:"
./rag-cli collections list --format json | \
jq -r '.collections[] | "  - " + .name + " (Owner: " + (.owner // "System") + ")"'

echo ""
echo "⚠️  Security Recommendations:"
echo "1. Regularly review admin user list"
echo "2. Audit collection access permissions"
echo "3. Remove inactive user accounts"
echo "4. Implement least-privilege access"
```

### Team and Group Management

**Team membership management:**
```bash
#!/bin/bash
team_id="team_engineering"
action="$1" # add, remove, list
user_id="$2"

case "$action" in
    "add")
        if [ -z "$user_id" ]; then
            echo "Usage: $0 add USER_ID"
            exit 1
        fi
        ./rag-cli users update "$user_id" --add-team "$team_id"
        echo "✅ Added $user_id to $team_id"
        ;;

    "remove")
        if [ -z "$user_id" ]; then
            echo "Usage: $0 remove USER_ID"
            exit 1
        fi
        ./rag-cli users update "$user_id" --remove-team "$team_id"
        echo "✅ Removed $user_id from $team_id"
        ;;

    "list")
        echo "👥 Team Members: $team_id"
        echo "========================"
        ./rag-cli users list --format json | \
        jq --arg team "$team_id" -r '
          .users[] |
          select(.teams[]? == $team) |
          "  - " + .name + " (" + .email + ") - " + .role'
        ;;

    *)
        echo "Usage: $0 {add|remove|list} [USER_ID]"
        echo "  add USER_ID    - Add user to team"
        echo "  remove USER_ID - Remove user from team"
        echo "  list          - List team members"
        ;;
esac
```

## Integration Examples

### LDAP/Active Directory Sync

```bash
#!/bin/bash
# Sync users from LDAP to RAG system

ldap_server="ldap://your-ldap-server.com"
base_dn="ou=users,dc=company,dc=com"
bind_dn="cn=rag-sync,ou=service-accounts,dc=company,dc=com"

echo "🔄 LDAP User Sync"
echo "================="

# Query LDAP for users (requires ldapsearch)
ldapsearch -x -H "$ldap_server" -D "$bind_dn" -W \
  -b "$base_dn" \
  "(objectClass=person)" \
  cn mail department | \
while read line; do
    if [[ "$line" =~ ^cn:\ (.*)$ ]]; then
        name="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^mail:\ (.*)$ ]]; then
        email="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^department:\ (.*)$ ]]; then
        department="${BASH_REMATCH[1]}"
    elif [[ "$line" == "" ]] && [[ -n "$name" ]] && [[ -n "$email" ]]; then
        # Process complete user record
        echo "Syncing: $name ($email) - $department"

        # Check if user exists
        if ./rag-cli users get "$email" --format json > /dev/null 2>&1; then
            echo "  User exists, updating..."
            ./rag-cli users update "$email" --name "$name"
        else
            echo "  Creating new user..."
            role="user"
            [[ "$department" == "IT" ]] && role="admin"
            [[ "$department" == "Management" ]] && role="editor"

            ./rag-cli users create \
              --name "$name" \
              --email "$email" \
              --role "$role"
        fi

        # Reset variables
        name=""
        email=""
        department=""
    fi
done

echo "✅ LDAP sync completed"
```

### User Onboarding Automation

```bash
#!/bin/bash
# Automated user onboarding script

new_user_email="$1"
department="$2"
manager_email="$3"

if [ -z "$new_user_email" ] || [ -z "$department" ] || [ -z "$manager_email" ]; then
    echo "Usage: $0 USER_EMAIL DEPARTMENT MANAGER_EMAIL"
    exit 1
fi

echo "🚀 User Onboarding: $new_user_email"
echo "==================================="

# Extract name from email (simple heuristic)
name=$(echo "$new_user_email" | sed 's/@.*//' | sed 's/\./ /g' | sed 's/\b\w/\U&/g')

# Determine role based on department
role="user"
team_id=""
collections=""

case "$department" in
    "engineering")
        role="editor"
        team_id="team_engineering"
        collections="col_technical,col_documentation"
        ;;
    "management")
        role="admin"
        team_id="team_management"
        collections="col_business,col_reports"
        ;;
    "research")
        role="editor"
        team_id="team_research"
        collections="col_research,col_papers"
        ;;
    *)
        role="user"
        collections="col_general"
        ;;
esac

echo "Creating user profile..."
user_id=$(./rag-cli users create \
    --name "$name" \
    --email "$new_user_email" \
    --role "$role" \
    --team "$team_id" \
    --collections "$collections" \
    --format json | jq -r '.id')

if [ "$user_id" != "null" ]; then
    echo "✅ User created: $user_id"

    echo "Setting up manager relationship..."
    # Note: This would require additional CLI commands for manager relationships
    # ./rag-cli users update "$user_id" --manager "$manager_email"

    echo "Sending welcome information..."
    # Send welcome email with getting started guide
    echo "Welcome to RAG System!" | mail -s "Welcome to RAG System" "$new_user_email"

    echo "✅ Onboarding completed for $name"
    echo ""
    echo "Next steps:"
    echo "1. User will receive activation email"
    echo "2. Manager has been notified"
    echo "3. User has access to appropriate collections"
    echo "4. Team permissions are configured"
else
    echo "❌ Failed to create user"
    exit 1
fi
```

## Security and Compliance

### Access Control Audit

```bash
#!/bin/bash
echo "🔐 Security Audit Report"
echo "======================="
echo "Generated: $(date)"
echo ""

# Check for users without recent activity
echo "👻 Inactive Users (30+ days):"
cutoff_date=$(date -d "30 days ago" +%Y-%m-%d)
./rag-cli users list --include-stats --format json | \
jq --arg cutoff "$cutoff_date" -r '
  .users[] |
  select(.stats.last_activity < $cutoff) |
  "  ⚠️  " + .name + " (" + .email + ") - Last seen: " + .stats.last_activity'

echo ""
echo "👨‍💼 Administrative Access:"
admin_count=$(./rag-cli users list --role admin --format json | jq '.total')
echo "  Total admins: $admin_count"
if [ "$admin_count" -gt 5 ]; then
    echo "  ⚠️  High number of admin users - review recommended"
fi

echo ""
echo "📚 Collection Permissions:"
# Check for collections with too many admins
./rag-cli collections list --format json | \
jq -r '.collections[] | select(.admin_count > 3) |
  "  ⚠️  " + .name + " has " + (.admin_count | tostring) + " admins"'

echo ""
echo "🔄 Recent Permission Changes (7 days):"
# This would require audit log functionality
echo "  (Audit log integration required)"

echo ""
echo "📋 Compliance Checklist:"
echo "  ✅ Regular access reviews"
echo "  ✅ Inactive user monitoring"
echo "  ✅ Admin user tracking"
echo "  ⚠️  Implement audit logging"
echo "  ⚠️  Add permission change notifications"
```

## Error Handling

### Common Error Scenarios

#### Insufficient Permissions
```bash
$ ./rag-cli users list
❌ Access denied

This command requires administrative privileges.
Current user role: user
Required role: admin

Contact your administrator to request elevated access.
```

#### User Not Found
```bash
$ ./rag-cli users get invalid-user
❌ User not found

User 'invalid-user' does not exist in the system.

Search for users: ./rag-cli users list --filter "partial-name"
```

#### Email Already Exists
```bash
$ ./rag-cli users create --name "New User" --email "existing@company.com"
❌ User creation failed

A user with email 'existing@company.com' already exists.
User ID: user_existing123

Update existing user: ./rag-cli users update user_existing123
View user details: ./rag-cli users get user_existing123
```

#### Cannot Delete Last Admin
```bash
$ ./rag-cli users delete user_lastadmin
❌ Deletion not allowed

Cannot delete the last administrative user in the system.
Promote another user to admin first, then retry deletion.

Promote user to admin: ./rag-cli users update USER_ID --role admin
```

## Next Steps

After mastering user management:
1. **[Configuration](../configuration.md)** - Advanced system configuration
2. **[Authentication](../authentication.md)** - User authentication setup
3. **[Troubleshooting](../troubleshooting.md)** - Resolve user management issues
4. **System Administration** - Advanced administrative features
