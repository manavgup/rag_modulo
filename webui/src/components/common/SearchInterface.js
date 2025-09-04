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
  InlineLoading,
  AccordionItem,
  Accordion
} from '@carbon/react';
import { Search, Filter, Document } from '@carbon/icons-react';
import { getUserCollections, searchDocuments } from '../../api/api';
import { useNotification } from '../../contexts/NotificationContext';
import './SearchInterface.css';

const SearchInterface = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [collections, setCollections] = useState([]);
  const [selectedCollection, setSelectedCollection] = useState('all');
  const [dateRange, setDateRange] = useState({ start: null, end: null });
  const [documentType, setDocumentType] = useState('all');
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false);
  const { addNotification } = useNotification();

  const sortChunksByPage = (chunks) => {
    return [...chunks].sort((a, b) => {
      const pageA = a.metadata?.page_number || 0;
      const pageB = b.metadata?.page_number || 0;
      return pageA - pageB;
    });
  };

  useEffect(() => {
    fetchCollections();
  }, []);

  const fetchCollections = async () => {
    try {
      const userCollections = await getUserCollections();
      const collections = userCollections?.collections? [
              { id: "all", name: "All Collections" },
              ...userCollections.collections.map((collection) => ({
                id: collection.id || collection.collection_id,
                name: collection.name,
              })),
            ]
          : [{ id: "all", name: "All Collections" }];
      setCollections(collections);
    } catch (error) {
      console.error('Error fetching collections:', error);
      addNotification('error', 'Error', 'Failed to fetch collections. Please try again later.');
      // Set default collections array even on error
      setCollections([{ id: "all", name: "All Collections" }]);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);

    try {
      const searchResult = await searchDocuments(query, selectedCollection);
      
      // Group source documents by document_id
      const groupedSources = searchResult.query_results.reduce((acc, result) => {
        const docId = result.chunk.document_id || 'unknown';
        if (!acc[docId]) {
          // Find corresponding document metadata
          const docMetadata = searchResult.documents.find(
            doc => docId === result.chunk.document_id
          ) || {};

 

          acc[docId] = {
            documentId: docId,
            title: docMetadata.document_name || 'Untitled Document',
            source: result.chunk.metadata?.source || 'unknown',
            chunks: []
          };
        }
        acc[docId].chunks.push({
          text: result.chunk.text,
          metadata: result.chunk.metadata,
          score: result.score
        });
        return acc;
      }, {});

      // Sort chunks by page number within each document
      Object.values(groupedSources).forEach(group => {
        group.chunks = sortChunksByPage(group.chunks);
      });

      setResults({
        answer: searchResult.answer,
        rewrittenQuery: searchResult.rewritten_query,
        sources: Object.values(groupedSources),
        evaluation: searchResult.evaluation,
      });

      if (Object.keys(groupedSources).length === 0) {
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

  const renderSourceHeader = (source) => (
    <div className="source-header">
      <Document size={20} />
      <span>{source.title}</span>
      <Tag type="gray" size="sm">{source.source}</Tag>
      <Tag type="blue" size="sm">{`${source.chunks.length} matches`}</Tag>
    </div>
  );

  const renderSourceMetadata = (metadata) => {
    if (!metadata) return null;
    
    const items = [];
    if (metadata.page_number) {
      items.push(`Page ${metadata.page_number}${metadata.total_pages ? ` of ${metadata.total_pages}` : ''}`);
    }
    if (metadata.source) {
      items.push(metadata.source);
    }
    if (metadata.created_at) {
      items.push(new Date(metadata.created_at).toLocaleDateString());
    }
    
    return items.length > 0 ? (
      <div className="source-metadata">
        {items.map((item, index) => (
          <Tag key={index} type="blue" size="sm">{item}</Tag>
        ))}
      </div>
    ) : null;
  };

  const getColor = (rate) => {
        if (rate === 'High') return 'green';
        if (rate === 'Medium') return 'orange';
        return 'red';
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
            onKeyUp={handleKeyPress}
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
      ) : results ? (
        <div className="search-results">
          {/* Main Answer Section */}
          <Tile className="answer-section">
            <h4>Answer</h4>
            <p>{results.answer}</p>
            {results.rewrittenQuery && (
              <div className="rewritten-query">
                <small>Rewritten query: {results.rewrittenQuery}</small>
              </div>
            )}
          </Tile>

          {/* Sources Section */}
          <div className="sources-section">
            <h4>Sources</h4>
            <Accordion>
              {results.sources.map((source, sourceIndex) => (
                <AccordionItem
                  key={sourceIndex}
                  title={renderSourceHeader(source)}
                >
                  {source.chunks.map((chunk, chunkIndex) => (
                    <Tile key={chunkIndex} className="source-chunk">
                      {renderSourceMetadata(chunk.metadata)}
                      <p>{highlightSearchTerms(chunk.text)}</p>
                      {chunk.score && (
                        <div className="chunk-score">
                          <small>Relevance Score: {(chunk.score * 100).toFixed(2)}%</small>
                        </div>
                      )}
                    </Tile>
                  ))}
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        {results.evaluation && results.evaluation.faithfulness && results.evaluation.answer_relevance && results.evaluation.context_relevance && (
          <div className="evaluation-section">
            <h4>Evaluation</h4>
            <Accordion>
              <AccordionItem title="Faithfulness">
                <span style={{ color: getColor(results.evaluation.faithfulness.faithfulness_rate) }}>
                  <p>{results.evaluation.faithfulness.faithfulness_rate}</p>
                </span>
                <p>{results.evaluation.faithfulness.reasoning}</p>
              </AccordionItem>
              <AccordionItem title="Answer Relevance">
                <span style={{ color: getColor(results.evaluation.answer_relevance.answer_relevance_rate) }}>
                  <p>{results.evaluation.answer_relevance.answer_relevance_rate}</p>
                </span>
                <p>{results.evaluation.answer_relevance.reasoning}</p>
              </AccordionItem>
              <AccordionItem title="Context Relevance">
                <span style={{ color: getColor(results.evaluation.context_relevance.context_relevance_rate) }}>
                  <p>{results.evaluation.context_relevance.context_relevance_rate}</p>
                </span>
                <p>{results.evaluation.context_relevance.reasoning}</p>
              </AccordionItem>
            </Accordion>
          </div>
        )}
          </div>
      ) : (
        <Tile className="no-results">
          <h4>No Results Found</h4>
          <p>Your search did not match any documents in the selected collection.</p>
          <p>Try:</p>
          <ul>
            <li>Using different keywords</li>
            <li>Checking if the collection has documents</li>
            <li>Selecting a different collection</li>
          </ul>
        </Tile>
      )}
    </div>
  );
};

export default SearchInterface;
