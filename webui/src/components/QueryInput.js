// components/QueryInput.js
import React from 'react';
import { TextInput, Button } from '@carbon/react';

const QueryInput = ({ query, setQuery, onSearch }) => {
  return (
    <div className="query-input">
      <TextInput
        id="query-input"
        labelText="Enter your query"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <Button onClick={onSearch}>Search</Button>
    </div>
  );
};

export default QueryInput;