# Sprint 3: Frontend Structure

## Objectives
- Set up the frontend architecture using React and IBM Carbon Design
- Implement core components and pages
- Set up routing and state management
- Implement API integration

## Steps

1. Set up project structure
   ```
   webui/
   ├── public/
   ├── src/
   │   ├── api/
   │   ├── components/
   │   ├── config/
   │   ├── contexts/
   │   ├── pages/
   │   ├── services/
   │   └── styles/
   ├── package.json
   └── Dockerfile.frontend
   ```

2. Set up routing
   - Install react-router-dom
   - Create main routes in App.js

3. Implement core components
   - Create Header component
   - Create NavigationBar component
   - Create SideNav component
   - Create QueryInput component
   - Create ResultsDisplay component
   - Create ErrorBoundary component

4. Implement main pages
   - Create HomePage
   - Create Dashboard
   - Create DashboardSettings
   - Create CollectionForm
   - Create IngestionSettings

5. Set up state management
   - Create AuthContext for user authentication
   - Implement React Query for server state management

6. Set up API service
   - Create api.js in the api/ directory for API calls using axios

7. Implement UI theme
   - Set up IBM Carbon Design theme
   - Create global styles in styles/carbon-overrides.scss

8. Implement authentication flow
   - Create SignIn component
   - Implement Auth component for handling authentication

9. Set up error handling
   - Implement ErrorBoundary component
   - Create error handling utilities

10. Implement basic tests
    - Set up Jest and React Testing Library
    - Write tests for core components

## Frontend Structure
```
webui/
├── public/
│   ├── index.html
│   ├── favicon.ico
│   └── manifest.json
├── src/
│   ├── api/
│   │   └── api.js
│   ├── components/
│   │   ├── Auth.js
│   │   ├── CollectionForm.js
│   │   ├── Dashboard.js
│   │   ├── DashboardSettings.js
│   │   ├── ErrorBoundary.js
│   │   ├── Header.js
│   │   ├── IngestionSettings.js
│   │   ├── NavigationBar.js
│   │   ├── QueryInput.js
│   │   ├── ResultsDisplay.js
│   │   ├── SideNav.js
│   │   └── SignIn.js
│   ├── config/
│   │   └── config.js
│   ├── contexts/
│   │   └── AuthContext.js
│   ├── pages/
│   │   ├── HomePage.js
│   │   └── HomePage.css
│   ├── services/
│   │   └── authService.js
│   ├── styles/
│   │   └── carbon-overrides.scss
│   ├── App.js
│   ├── App.css
│   └── index.js
├── package.json
└── Dockerfile.frontend
```

## Completion Criteria
- [ ] Project structure set up
- [ ] Routing implemented
- [ ] Core components created
- [ ] Main pages implemented
- [ ] State management set up
- [ ] API service created
- [ ] UI theme and global styles set up
- [ ] Authentication flow implemented
- [ ] Error handling implemented
- [ ] Basic tests written and passing

## Next Steps
Proceed to 04_coreFunctionality.md for implementing the core functionality of the application.