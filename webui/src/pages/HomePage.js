// pages/HomePage.js
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
import Settings from '../components/Settings';
import './HomePage.css';

const HomePage = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isSideNavExpanded, setIsSideNavExpanded] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [llmSettings, setLlmSettings] = useState({
    topK: 5,
    numTokens: 100,
    temperature: 0.7,
  });

  const toggleSideNav = () => setIsSideNavExpanded(!isSideNavExpanded);

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

  const handleExampleClick = (question) => {
    setQuery(question);
    handleSearch();
  };

  const handleNavigation = (e, page) => {
    e.preventDefault();
    setCurrentPage(page);
    if (page === 'settings') {
      setIsSettingsModalOpen(true);
    }
  };

  const exampleQuestions = [
    "What is included in my Northwind Health Plus plan that is not in standard?",
    "What happens in a performance review?",
    "What does a Product Manager do?"
  ];

  return (
    <div className="homepage">
      <Header 
        onMenuClick={toggleSideNav}
        onSettingsClick={() => setIsSettingsModalOpen(true)}
      />
      <UISideNav 
        expanded={isSideNavExpanded} 
        onNavigate={handleNavigation}
      />
      <Content>
        <div className="top-actions">
          <Button kind="ghost" size="sm" onClick={clearSearch}>Clear chat</Button>
          <Button kind="ghost" size="sm" onClick={() => setIsSettingsModalOpen(true)}>
            <SettingsIcon size={16} /> Developer settings
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

        {currentPage === 'report1' && <div>Report 1 Content</div>}
        {currentPage === 'report2' && <div>Report 2 Content</div>}

        <Settings
          isOpen={isSettingsModalOpen}
          onClose={() => setIsSettingsModalOpen(false)}
          settings={llmSettings}
          onSettingsChange={handleSettingsChange}
        />
      </Content>
    </div>
  );
};

export default HomePage;