// components/QueryInput.js
import React from 'react';
import { TextInput, IconButton } from '@carbon/react';
import { Send } from '@carbon/icons-react';

const QueryInput = ({ query, setQuery, onSearch }) => {
  return (
    <div className="query-input">
      <TextInput
        id="query-input"
        labelText="Enter your query"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className='query-text-input'
      />
      <IconButton
        onClick={onSearch}
        renderIcon={Send}
        iconDescription="Send"
        className="send-icon-button"
        hasIconOnly
        kind='primary'
        size='field'
      />
    </div>
  );
};

export default QueryInput;
