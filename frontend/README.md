# RAG Modulo Agentic Frontend

A modern, responsive React frontend for the RAG Modulo Agentic Platform built with IBM Carbon Design System.

## 🚀 Features

### Core Components
- **Dashboard**: Comprehensive overview with system metrics, quick actions, and recent activity
- **Search Interface**: Advanced document search with filters, highlights, and saved searches
- **Agent Orchestration**: AI agent management and workflow coordination
- **Workflow Designer**: Visual workflow creation and management
- **Document Management**: Upload, organize, and manage document collections
- **Analytics Dashboard**: Usage analytics and performance monitoring
- **System Configuration**: Admin settings and system management

### Key Features
- **Responsive Design**: Mobile-first approach with Carbon Design System
- **Dark Mode Support**: Automatic dark mode detection and manual toggle
- **Real-time Notifications**: Toast notifications for user feedback
- **Advanced Search**: AI-powered search with filters, highlights, and saved searches
- **Interactive Dashboards**: Rich data visualization and metrics
- **Accessibility**: WCAG compliant with keyboard navigation support

## 🛠️ Technology Stack

- **React 18**: Modern React with hooks and functional components
- **TypeScript**: Type-safe development with strict typing
- **IBM Carbon Design System**: Enterprise-grade UI components
- **CSS3**: Custom styling with CSS Grid and Flexbox
- **React Router**: Client-side routing and navigation
- **Context API**: State management for global application state

## 📁 Project Structure

```
frontend/
├── public/
│   ├── index.html
│   └── manifest.json
├── src/
│   ├── components/
│   │   ├── admin/
│   │   │   └── SystemConfiguration.tsx
│   │   ├── agent/
│   │   │   └── AgentOrchestration.tsx
│   │   ├── analytics/
│   │   │   └── AnalyticsDashboard.tsx
│   │   ├── auth/
│   │   │   └── LoginPage.tsx
│   │   ├── common/
│   │   │   └── NotificationToast.tsx
│   │   ├── dashboard/
│   │   │   ├── Dashboard.tsx
│   │   │   └── Dashboard.css
│   │   ├── document/
│   │   │   └── DocumentManagement.tsx
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Header.css
│   │   │   ├── Layout.tsx
│   │   │   └── SideNav.tsx
│   │   ├── search/
│   │   │   ├── SearchInterface.tsx
│   │   │   └── SearchInterface.css
│   │   └── workflow/
│   │       └── WorkflowDesigner.tsx
│   ├── contexts/
│   │   ├── AgentContext.tsx
│   │   ├── AuthContext.tsx
│   │   ├── NotificationContext.tsx
│   │   └── WorkflowContext.tsx
│   ├── App.tsx
│   ├── App.css
│   ├── global.css
│   └── index.tsx
├── package.json
├── tsconfig.json
└── README.md
```

## 🎨 Design System

### Color Palette
- **Primary**: IBM Blue (#0f62fe)
- **Secondary**: IBM Purple (#8a3ffc)
- **Success**: IBM Green (#198038)
- **Warning**: IBM Orange (#ff832b)
- **Error**: IBM Red (#da1e28)
- **Neutral**: IBM Gray (#525252)

### Typography
- **Headings**: IBM Plex Sans (600-700 weight)
- **Body**: IBM Plex Sans (400-500 weight)
- **Code**: IBM Plex Mono

### Spacing
- **Base Unit**: 8px
- **Small**: 0.5rem (8px)
- **Medium**: 1rem (16px)
- **Large**: 1.5rem (24px)
- **XLarge**: 2rem (32px)

## 🚀 Getting Started

### Prerequisites
- Node.js 16+
- npm 8+

### Installation
```bash
cd frontend
npm install
```

### Development
```bash
npm start
```
Runs the app in development mode at [http://localhost:3000](http://localhost:3000)

### Building
```bash
npm run build
```
Creates an optimized production build in the `build` folder.

### Testing
```bash
npm test
```
Runs the test suite in interactive watch mode.

## 📱 Responsive Breakpoints

- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

## 🎯 Component Features

### Dashboard
- **System Overview**: Real-time metrics and KPIs
- **Quick Actions**: One-click access to main features
- **Recent Activity**: Live activity feed with status indicators
- **System Status**: Health monitoring with progress bars
- **Quick Statistics**: Detailed performance metrics table

### Search Interface
- **Advanced Search**: Multi-field search with AI-powered results
- **Smart Filters**: Collection, date range, document type, and agent filters
- **Search History**: Persistent search history with quick access
- **Saved Searches**: Bookmark frequently used searches
- **Result Highlights**: AI-powered content highlighting
- **Export & Share**: Export results and share searches

### Agent Orchestration
- **Agent Management**: Create, edit, and manage AI agents
- **Session Monitoring**: Real-time session tracking and control
- **Task Management**: Task assignment and progress monitoring
- **Agent Marketplace**: Browse and configure available agents

### Workflow Designer
- **Visual Designer**: Drag-and-drop workflow creation
- **Template Library**: Pre-built workflow templates
- **Execution Monitoring**: Real-time workflow execution tracking
- **Version Control**: Workflow versioning and rollback

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the frontend directory:

```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_APP_NAME=RAG Modulo Agentic Platform
```

### Customization
- **Themes**: Modify `App.css` for global theme changes
- **Components**: Each component has its own CSS file for styling
- **Icons**: Replace Carbon icons with custom icons as needed
- **Layout**: Modify `Layout.tsx` for structural changes

## 🧪 Testing

### Unit Tests
```bash
npm test
```

### E2E Tests
```bash
npm run test:e2e
```

### Coverage
```bash
npm run test:coverage
```

## 📦 Deployment

### Production Build
```bash
npm run build
```

### Docker
```dockerfile
FROM nginx:alpine
COPY build/ /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Static Hosting
The build folder can be deployed to any static hosting service:
- Vercel
- Netlify
- AWS S3 + CloudFront
- GitHub Pages

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Contact the development team

## 🔮 Roadmap

### Phase 1 (Current)
- ✅ Core UI components
- ✅ Responsive design
- ✅ Basic functionality

### Phase 2 (Next)
- 🔄 API integration
- 🔄 Real-time updates
- 🔄 Advanced analytics

### Phase 3 (Future)
- ⏳ Mobile app
- ⏳ Offline support
- ⏳ Advanced AI features

---

Built with ❤️ using React and IBM Carbon Design System
