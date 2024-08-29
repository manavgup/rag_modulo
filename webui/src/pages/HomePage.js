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

const HomePage = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isSideNavExpanded, setIsSideNavExpanded] = useState(false);
  const [isDashboardSettingsModalOpen, setIsDashboardSettingsModalOpen] = useState(false);
  const [isIngestionSettingsModalOpen, setIsIngestionSettingsModalOpen] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [llmSettings, setLlmSettings] = useState({
    topK: 5,
    numTokens: 100,
    temperature: 0.7,
  });
  const [ingestionSettings, setIngestionSettings] = useState({
    chunking_strategy: 5,
    chunk_overlap: 10,
    chunk_size: 0.5,
    database: 'Milvus',
  });

  const toggleSideNav = () => {
    setIsSideNavExpanded(prevState => !prevState);
  };

  const handleSearch = async () => {
    console.log('Searching:', query);
    setResults([
      { id: 1, title: "Result 1", snippet: "This is the first result" },
      { id: 2, title: "Result 2", snippet: "This is the second result" },
    ]);
    setHasSearched(true);
  };

  const clearSearch = () => {
    setQuery('');
    setResults([]);
    setHasSearched(false);
  };

  const handleSettingsChange = (setting, value) => {
    setLlmSettings(prev => ({ ...prev, [setting]: value }));
  };

  const handleIngestionSettingsChange = (setting, value) => {
    setIngestionSettings(prev => ({ ...prev, [setting]: value }));
  };

  const handleExampleClick = (question) => {
    setQuery(question);
    handleSearch();
  };

  const handleNavigation = (e, page) => {
    e.preventDefault();
    console.log(`Navigating to: ${page}`);
    setCurrentPage(page);
    setIsDashboardSettingsModalOpen(false);
    setIsIngestionSettingsModalOpen(false);
    setIsSideNavExpanded(false); // Close SideNav on navigation
  };

  const exampleQuestions = [
    "What is included in my Northwind Health Plus plan that is not in standard?",
    "What happens in a performance review?",
    "What does a Product Manager do?"
  ];

  const handleFormSubmit = (data) => {
    console.log('Form data submitted:', data);
  };

  return (
    <div className="homepage">
      <Header onMenuClick={toggleSideNav} />
      <div className="main-container">
        <UISideNav 
          expanded={isSideNavExpanded} 
          onNavigate={handleNavigation}
          currentPage={currentPage}
        />
        <Content className={`main-content ${isSideNavExpanded ? 'content-shifted' : ''}`}>
          <div className="top-actions">
            <Button kind="ghost" size="sm" onClick={clearSearch}>Clear chat</Button>
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

          {currentPage === 'dashboard' && (
            <>
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

              <QueryInput 
                query={query}
                setQuery={setQuery}
                onSearch={handleSearch}
              />

              {hasSearched && <ResultsDisplay results={results} />}
            </>
          )}

          {currentPage === 'create' && (
            <CollectionForm onSubmit={handleFormSubmit} />
          )}

          {currentPage === 'report1' && <div>Report 1 Content</div>}
          {currentPage === 'report2' && <div>Report 2 Content</div>}

          <DashboardSettings
            isOpen={isDashboardSettingsModalOpen}
            onClose={() => setIsDashboardSettingsModalOpen(false)}
            settings={llmSettings}
            onSettingsChange={handleSettingsChange}
          />

          <IngestionSettings
            isOpen={isIngestionSettingsModalOpen}
            onClose={() => setIsIngestionSettingsModalOpen(false)}
            settings={ingestionSettings}
            onSettingsChange={handleIngestionSettingsChange}
          />
        </Content>
      </div>
    </div>
  );
};

export default HomePage;