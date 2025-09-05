import React from 'react';
import { DataTable, Table, TableBody, TableCell, TableContainer, TableHead, TableHeader, TableRow, InlineNotification } from '@carbon/react';

const ResultsDisplay = ({ results }) => {
  const headers = [
    { key: 'id', header: 'ID' },
    { key: 'title', header: 'Title' },
    { key: 'snippet', header: 'Snippet' },
  ];

  return (
    <TableContainer title="Search Results">
      {results.length === 0 ? (
        <InlineNotification
          kind="info"
          title="No Results"
          subtitle="There are no results to display."
        />
      ) : (
        <DataTable rows={results} headers={headers}>
          {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
            <Table {...getTableProps()}>
              <TableHead>
                <TableRow>
                  {headers.map((header) => (
                    <TableHeader {...getHeaderProps({ header })}>
                      {header.header}
                    </TableHeader>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => (
                  <TableRow {...getRowProps({ row })}>
                    {row.cells.map((cell) => (
                      <TableCell key={cell.id}>{cell.value}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </DataTable>
      )}
    </TableContainer>
  );
};

export default ResultsDisplay;
