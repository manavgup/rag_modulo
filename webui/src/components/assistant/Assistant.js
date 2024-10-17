import React, { useEffect, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import {
  Button,
  Content,
  Row,
  DataTable,
  Loading,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableToolbar,
  TableToolbarAction,
  TableToolbarContent,
  TableToolbarMenu,
  TableToolbarSearch,
  OverflowMenu,
  OverflowMenuItem,
  Column,
  FlexGrid,
  Pagination,
} from "@carbon/react";
import { Add, Play } from "@carbon/icons-react";

import { getAssistants } from "src/api/api_assistant";

import "./Assistant.css";
import "src/styles/view-ui.css";
import { Icon } from "carbon-components-react";

const Assistants = () => {
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoadingAssistants, setIsLoadingAssistants] = useState(false);
  const [userAssistants, setAssistants] = useState([]);
  const [tableDataRows, setTableDataRows] = useState([]);
  const [selectedAssistant, setSelectedAssistant] = useState([]);

  const headers = [
    { key: "query", header: "Query" },
    { key: "response", header: "Response" },
    { key: "context", header: "Context" },
    { key: "max_tokens", header: "Max Tokens" },
    { key: "confidence", header: "Confidence" }
  ];

  useEffect(() => {
    fetchAssistants();
  }, []);

  const fetchAssistants = async () => {
    setIsLoadingAssistants(true);
    try {
      const assistants = await getAssistants();
      const updatedKeys = assistants.map(({ assistant_id: id, ...rest }) => ({
        id,
        ...rest,
      }));
      const updatedValues = updatedKeys.map((obj) => ({
        ...obj,
        is_private: obj.is_private ? "true" : "false",
      }));
      setAssistants(Array.isArray(updatedValues) ? updatedValues : []);
      setTableDataRows(updatedValues.slice(0, 5));
    } catch (error) {
      console.error("Error fetching user assistants:", error);
      setErrorMessage("Failed to fetch user assistants. Please try again later.");
    } finally {
      setIsLoadingAssistants(false);
    }
  };

  const createNewAssistant = () => {
    navigate("/assistants/create", { replace: true });
  };

  const onClickAssistantTable = (assistantId) => {
    setSelectedAssistant(
      userAssistants.find((assistant) => assistant.id === assistantId)
    );
  };

  const pageOnChange = (e) => {
    setTableDataRows(
      userAssistants.slice((e.page - 1) * e.pageSize, e.page * e.pageSize)
    );
  };

  const runAssistant = () => {
    console.log('Call api to run assistant')
  }

  return (
    <Content className="children-container view-content">
      <div className="view-title">
        <h2>Assistants</h2>
        <Button renderIcon={Add} aria-label="Add new assistant" onClick={createNewAssistant}>
          New Assistant
        </Button>
      </div>

      {isLoadingAssistants ? (
        <div className="data-loading">
          <Loading description="Loading assistants" withOverlay={false} />
        </div>
      ) : (
        <>
          <DataTable rows={tableDataRows} headers={headers}>
            {({ rows, headers, getTableProps, getHeaderProps, getRowProps, onInputChange }) => (
              <>
                <TableToolbar>
                  <div className="view-datatable-header">Any header text about the data below...</div>
                  <TableToolbarContent>
                    <TableToolbarSearch onChange={onInputChange} />
                    <TableToolbarMenu>
                      <TableToolbarAction onClick={() => {}}>Action 1</TableToolbarAction>
                      <TableToolbarAction onClick={() => {}}>Action 2</TableToolbarAction>
                      <TableToolbarAction onClick={() => {}}>Action 3</TableToolbarAction>
                    </TableToolbarMenu>
                  </TableToolbarContent>
                </TableToolbar>

                <Table {...getTableProps()}>
                  <TableHead key="table-head">
                    <TableRow>
                      {headers.map((header, idx) => (
                        <TableHeader {...getHeaderProps({ header, isSortable: true })} key={idx}>
                          {header.header}
                        </TableHeader>
                      ))}
                      <TableHeader key="column-menu-header" className="view-tabledata-action"></TableHeader>
                      <TableHeader key="column-menu-header" className="view-tabledata-action"></TableHeader>
                    </TableRow>
                  </TableHead>
                  <TableBody key="table-body">
                    {rows.map((row, idx) => (
                      <TableRow {...getRowProps({ row })} key={idx} onClick={() => onClickAssistantTable(row.id)}>
                        {row.cells.map((cell) => (
                          <TableCell key={cell.id}>{cell.value}</TableCell>
                        ))}
                        <TableCell key="column-menu" className="cds--table-column-menu">
                          <Button renderIcon={Play} size="sm" iconDescription="Run Assistant" hasIconOnly onClick={runAssistant}/>
                        </TableCell>
                        <TableCell key="column-menu" className="cds--table-column-menu">
                          <OverflowMenu size="sm" flipped aria-label="options 1">
                            <OverflowMenuItem key="item-1" itemText="View Assistant" />
                            <OverflowMenuItem key="item-2" itemText="Edit Assistant" />
                            <OverflowMenuItem key="item-3" itemText="Delete Assistant" />
                          </OverflowMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </>
            )}
          </DataTable>
          <Pagination
            disabled={false}
            page="1"
            totalItems={userAssistants.length}
            pageSize="5"
            onChange={pageOnChange}
            pageSizes={[5, 10, 20, 50]}
            size="md"
          />
        </>
      )}
    </Content>
  );
};

export default Assistants;
