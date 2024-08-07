// Importing necessary libraries and components
import React, { useState } from 'react';
import {
  Content,
  Button,
  ClickableTile,
} from '@carbon/react';
import { Settings as SettingsIcon } from '@carbon/icons-react';
import Header from '../components/Header.js';
import UISideNav from '../components/SideNav.js';
import QueryInput from '../components/QueryInput';
import ResultsDisplay from '../components/ResultsDisplay';
import DashboardSettings from '../components/DashboardSettings';
import IngestionSettings from '../components/IngestionSettings';
import CollectionForm from '../components/CollectionForm';
import './HomePage.css';

// HomePage component definition
const HomePage = () => {
  // State variables for managing component state
  const [query, setQuery] = useState(''); // Search query
  const [results, setResults] = useState([]); // Search results
  const [isSideNavExpanded, setIsSideNavExpanded] = useState(false); // Sidebar toggle state
  const [isDashboardSettingsModalOpen, setIsDashboardSettingsModalOpen] = useState(false); // Dashboard settings modal state
  const [isIngestionSettingsModalOpen, setIsIngestionSettingsModalOpen] = useState(false); // Ingestion settings modal state
  const [hasSearched, setHasSearched] = useState(false); // Search state
  const [currentPage, setCurrentPage] = useState('dashboard'); // Current page state
  const [llmSettings, setLlmSettings] = useState({ // Settings for language model
    topK: 5,
    numTokens: 100,
    temperature: 0.7,
  });
  const [ingestionSettings, setIngestionSettings] = useState({ // Settings for ingestion
    chunking_strategy: 5,
    chunk_overlap: 10,
    chunk_size: 0.5,
    database: 'Milvus',
  });

  // Function to toggle sidebar visibility
  const toggleSideNav = () => setIsSideNavExpanded(!isSideNavExpanded);

  // Function to handle search
  const handleSearch = async () => {
    console.log('Searching:', query);
    setResults([
      { id: 1, title: "Result 1", snippet: "This is the first result" },
      { id: 2, title: "Result 2", snippet: "This is the second result" },
    ]);
    setHasSearched(true);
  };

  // Function to clear search results
  const clearSearch = () => {
    setQuery('');
    setResults([]);
    setHasSearched(false);
  };

  // Function to handle settings change
  const handleSettingsChange = (setting, value) => {
    setLlmSettings(prev => ({ ...prev, [setting]: value }));
  };

  // Function to handle ingestion settings change
  const handleIngestionSettingsChange = (setting, value) => {
    setIngestionSettings(prev => ({ ...prev, [setting]: value }));
  };

  // Function to handle example question click
  const handleExampleClick = (question) => {
    setQuery(question);
    handleSearch();
  };

  // Function to handle page navigation
  const handleNavigation = (e, page) => {
    e.preventDefault();
    console.log(`Navigating to: ${page}`);
    setCurrentPage(page);
    // Close both modals when navigating to a new page
    setIsDashboardSettingsModalOpen(false);
    setIsIngestionSettingsModalOpen(false);
  };

  // Example questions for quick search
  const exampleQuestions = [
    "What is included in my Northwind Health Plus plan that is not in standard?",
    "What happens in a performance review?",
    "What does a Product Manager do?"
  ];

  // Function to handle form submission
  const handleFormSubmit = (data) => {
    console.log('Form data submitted:', data);
    // Add your form submission logic here
  };

  return (
    <div className="homepage">
      {/* Header component with menu click handler */}
      <Header 
        onMenuClick={toggleSideNav} // Only this line remains, removed onSettingsClick prop
      />
      {/* Sidebar navigation component */}
      <UISideNav 
        expanded={isSideNavExpanded} 
        onNavigate={handleNavigation}
      />
      <Content>
        <div className="top-actions">
          {/* Button to clear search */}
          <Button kind="ghost" size="sm" onClick={clearSearch}>Clear chat</Button>
          {/* Button to open respective settings modal */}
          <Button kind="ghost" size="sm" onClick={() => {
            if (currentPage === 'dashboard') {
              setIsDashboardSettingsModalOpen(true);
            } else if (currentPage === 'create') {
              setIsIngestionSettingsModalOpen(true);
            }
          }}>
            <SettingsIcon size={16} /> {currentPage === 'dashboard' ? 'LLM Settings' : 'Ingestion Settings'}
          </Button>
        </div>

        {/* Conditional rendering based on current page */}
        {currentPage === 'dashboard' && (
          <>
            {/* Display example questions */}
            <div className="example-questions">
              {exampleQuestions.map((question, index) => (
                <ClickableTile
                  key={index}
                  onClick={() => handleExampleClick(question)}
                >
                  {question}
                </ClickableTile>
              ))}
            </div>

            {/* Query input component */}
            <QueryInput 
              query={query}
              setQuery={setQuery}
              onSearch={handleSearch}
            />

            {/* Results display component if search has been conducted */}
            {hasSearched && <ResultsDisplay results={results} />}
          </>
        )}

        {/* Conditional rendering for create page */}
        {currentPage === 'create' && (
          <CollectionForm onSubmit={handleFormSubmit} />
        )}

        {/* Placeholder for report 1 content */}
        {currentPage === 'report1' && <div>Report 1 Content</div>}
        {/* Placeholder for report 2 content */}
        {currentPage === 'report2' && <div>Report 2 Content</div>}

        {/* Dashboard settings modal component */}
        <DashboardSettings
          isOpen={isDashboardSettingsModalOpen}
          onClose={() => setIsDashboardSettingsModalOpen(false)}
          settings={llmSettings}
          onSettingsChange={handleSettingsChange}
        />

        {/* Ingestion settings modal component */}
        <IngestionSettings
          isOpen={isIngestionSettingsModalOpen}
          onClose={() => setIsIngestionSettingsModalOpen(false)}
          settings={ingestionSettings}
          onSettingsChange={handleIngestionSettingsChange}
        />
      </Content>
    </div>
  );
};

export default HomePage;
