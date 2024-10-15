import React from 'react';
import { Accordion, AccordionItem } from 'carbon-components-react';

const SearchResultsComponent = ({ results }) => {
  return (
    <Accordion>
      {results.map((result, index) => (
        <AccordionItem key={index} title={result.title}>
          <p>{result.excerpt}</p>
        </AccordionItem>
      ))}
    </Accordion>
  );
};

export default SearchResultsComponent;
