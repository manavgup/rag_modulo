# 🚀 Development Workflow Guide

## Quick Start (Hot Reloading)

For the **fastest development experience** with instant updates:

```bash
make dev-hotreload
```

This starts:
- 🔥 **React development server** with hot reloading at `http://localhost:3000`
- 🔧 **Backend API** with mock authentication at `http://localhost:8000`
- 📊 **MLflow** at `http://localhost:5001`

## Development Modes

### 1. Hot Reload Development (⚡ **RECOMMENDED**)

```bash
# Start development with hot reloading
make dev-hotreload

# View logs
make dev-hotreload-logs

# Restart services
make dev-hotreload-restart

# Stop development
make dev-hotreload-stop

# Check status
make dev-hotreload-status
```

**Features:**
- ✅ Edit React files → See changes instantly
- ✅ CSS/Tailwind updates → Live refresh
- ✅ Component changes → Fast refresh
- ✅ TypeScript support with live compilation
- ✅ Mock authentication enabled

### 2. Production-like Development

```bash
# Start with production builds (slower)
make dev-production
# or
make dev
```

**Use when:**
- Testing production builds
- Debugging nginx configuration
- Testing container behavior

### 3. Frontend-only Development

```bash
# Start only React dev server (no containers)
make frontend-only
```

**Use when:**
- You have backend running separately
- Working on frontend-only features
- Fastest possible frontend iteration

## Development Workflow Comparison

| Command | Frontend | Backend | Speed | Use Case |
|---------|----------|---------|-------|----------|
| `make dev-hotreload` | React dev server | Container | ⚡⚡⚡ | **Daily development** |
| `make dev` | Production build | Container | ⚡ | Testing builds |
| `make frontend-only` | React dev server | External | ⚡⚡⚡ | Frontend-only work |
| `make run-app` | **Now uses hot reload!** | Container | ⚡⚡⚡ | **Default choice** |

## Key Files Created

### Hot Reload Configuration
- `frontend/Dockerfile.dev` - Development container with React dev server
- `docker-compose.hotreload.yml` - Hot reload docker-compose configuration

### Volume Mounting Strategy
```yaml
volumes:
  # Mount specific directories for hot reload
  - ./frontend/src:/app/src
  - ./frontend/public:/app/public
  - ./frontend/package.json:/app/package.json
  # Exclude node_modules to prevent conflicts
  - /app/node_modules
```

### Environment Variables for Hot Reload
```bash
CHOKIDAR_USEPOLLING=true    # File watching in Docker
FAST_REFRESH=true           # React Fast Refresh
WATCHPACK_POLLING=true      # Webpack file watching
```

## Troubleshooting

### Hot Reload Not Working?
1. Check if files are being watched:
   ```bash
   make dev-hotreload-logs
   ```
2. Look for compilation errors in the logs
3. Ensure you're editing files in `frontend/src/`

### Port Conflicts?
- Hot reload uses port 3000 (React dev server)
- Production mode uses port 3000 (nginx)
- Make sure to stop one before starting the other

### Container Issues?
```bash
# Stop everything and start fresh
make dev-hotreload-stop
make dev-hotreload

# Or use the legacy approach
make dev-production
```

## Migration from Old Workflow

### Before (Slow)
```bash
# Old way - required rebuilding containers for changes
make build-frontend
make restart-frontend
```

### After (Fast)
```bash
# New way - instant hot reload
make dev-hotreload
# Edit files and see changes immediately!
```

## Performance Tips

1. **Use hot reload for daily development** - It's the fastest
2. **Use production builds before committing** - Test the real build
3. **Use frontend-only when working on UI** - Skip container overhead
4. **Keep node_modules excluded** - Prevents volume mount conflicts

## Next Steps

The new hot reload system includes our React infinite loop fixes, so you can now:

1. Start development: `make dev-hotreload`
2. Edit React components and see changes instantly
3. No more endless backend queries or frontend flickering!

Happy coding! 🎉
