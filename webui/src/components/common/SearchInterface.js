import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  TextInput,
  Button,
  Tile,
  Loading,
  DatePicker,
  DatePickerInput,
  Dropdown,
  Tag,
  ExpandableTile,
  InlineLoading
} from 'carbon-components-react';
import { Search, Filter } from '@carbon/icons-react';
import { getUserCollections } from '../../api/api'; // Removed queryCollection import
import { useNotification } from '../../contexts/NotificationContext';
import './SearchInterface.css';

const SearchInterface = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [collections, setCollections] = useState([]);
  const [selectedCollection, setSelectedCollection] = useState('all');
  const [dateRange, setDateRange] = useState({ start: null, end: null });
  const [documentType, setDocumentType] = useState('all');
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false);
  const { addNotification } = useNotification();

  useEffect(() => {
    fetchCollections();
  }, []);

  const fetchCollections = async () => {
    try {
      const userCollections = await getUserCollections();
      const collections =
        userCollections && userCollections.length > 0
          ? [
              { id: "all", name: "All Collections" },
              ...userCollections.map((collection) => ({
                id: collection.collection_id,
                name: collection.name,
              })),
            ]
          : [{ id: "all", name: "All Collections" }];
      setCollections(collections);
    } catch (error) {
      console.error('Error fetching collections:', error);
      addNotification('error', 'Error', 'Failed to fetch collections. Please try again later.');
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);

    try {
      // Define search logic or use another function instead of queryCollection
      // const searchResults = await someOtherFunction(searchParams);
      const searchResults = []; // Placeholder for demonstration
      setResults(searchResults);
      if (searchResults.length === 0) {
        addNotification('info', 'No Results', 'Your search did not match any documents.');
      }
    } catch (error) {
      console.error('Error performing search:', error);
      addNotification('error', 'Search Error', 'An error occurred while searching. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter') {
      handleSearch();
    }
  };

  const highlightSearchTerms = (text) => {
    if (!query) return text;
    const regex = new RegExp(`(${query.split(' ').join('|')})`, 'gi');
    return text.split(regex).map((part, index) => 
        regex.test(part) ? <mark key={index}>{part}</mark> : part
      );
  };

  return (
    <div className="children-container search-interface">
      <h3>Search Documents</h3>
      <Tile className="search-box">
        <div className="search-input-wrapper">
          <TextInput
            id="search-input"
            labelText="Enter your query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="E.g., What is RAG?"
          />
          <Button
            renderIcon={Search}
            onClick={handleSearch}
            disabled={!query.trim() || loading}
          >
            {loading ? <InlineLoading description="Searching..." /> : 'Search'}
          </Button>
        </div>
        <Button
          kind="ghost"
          renderIcon={Filter}
          onClick={() => setShowAdvancedSearch(!showAdvancedSearch)}
        >
          Advanced Search
        </Button>
        {showAdvancedSearch && (
          <div className="advanced-search-options">
            <Dropdown
              id="collection-select"
              titleText="Select Collection"
              items={collections}
              itemToString={(item) => (item ? item.name : '')}
              onChange={({ selectedItem }) => setSelectedCollection(selectedItem.id)}
              selectedItem={collections.find(c => c.id === selectedCollection)}
            />
            <DatePicker datePickerType="range" onChange={([start, end]) => setDateRange({ start, end })}>
              <DatePickerInput
                id="date-picker-start"
                placeholder="mm/dd/yyyy"
                labelText="Start Date"
              />
              <DatePickerInput
                id="date-picker-end"
                placeholder="mm/dd/yyyy"
                labelText="End Date"
              />
            </DatePicker>
            <Dropdown
              id="document-type-select"
              titleText="Document Type"
              items={['all', 'pdf', 'docx', 'txt']}
              onChange={({ selectedItem }) => setDocumentType(selectedItem)}
              selectedItem={documentType}
            />
          </div>
        )}
      </Tile>

      {loading ? (
        <Loading description="Searching..." withOverlay={false} />
      ) : (
        <div className="search-results">
          {results.map((result, index) => (
            <ExpandableTile key={index} className="result-item">
              <div className="result-header">
                <h3>{result.title || 'Untitled Document'}</h3>
                <div className="result-meta">
                  <Tag type="blue">{result.documentType}</Tag>
                  <span className="result-date">{new Date(result.date).toLocaleDateString()}</span>
                </div>
              </div>
              <div className="result-snippet">{highlightSearchTerms(result.snippet)}</div>
              <div className="result-expanded-content">
                <p>{highlightSearchTerms(result.content)}</p>
                <Link to={`/document/${result.id}`} className="view-document-link">
                  View Full Document
                </Link>
              </div>
            </ExpandableTile>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchInterface;
