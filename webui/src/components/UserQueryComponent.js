import React, { useState } from 'react';
import { TextInput, Button } from 'carbon-components-react';

const UserQueryComponent = () => {
  const [query, setQuery] = useState('');

  const handleSearch = async () => {
    // Call the search API and handle the response
    console.log('Searching for:', query);
  };

  return (
    <div>
      <TextInput
        id="search-query"
        labelText="Enter your query"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Type a natural language query..."
      />
      <Button onClick={handleSearch}>Search</Button>
    </div>
  );
};

export default UserQueryComponent;
