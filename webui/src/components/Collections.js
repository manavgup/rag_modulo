import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

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
  UnorderedList,
  ListItem,
  Pagination
} from "@carbon/react";
import { Add } from "@carbon/icons-react";

import { getUserCollections } from "../api/api";
import "../styles/view-ui.css";

const Collections = () => {
  let navigate = useNavigate();
  /* TODO: Add a messageQueue for the application */
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoadingCollections, setIsLoadingCollections] = useState(false);
  const [userCollections, setUserCollections] = useState([]);
  const [tableDataRows, setTableDataRows] = useState([]);
  const [selectedCollection, setSelectedCollection] = useState([]);

  const headers = [
    {
      key: "name",
      header: "Name",
    },
    {
      key: "is_private",
      header: "Private",
    },
    {
      key: "status",
      header: "Status",
    },
  ];

  useEffect(() => {
    fetchUserCollections();
  }, []);

  const fetchUserCollections = async () => {
    setIsLoadingCollections(true);
    try {
      const collections = (await getUserCollections())?.collections;
      console.log(collections);
      // setUserCollections(Array.isArray(collections) ? collections : []);

      // datatable requires a field called id
      const updatedKeys = collections.map(({ collection_id: id, ...rest }) => ({
        id,
        ...rest,
      }));

      // change other types fields to string
      const updatedValues = updatedKeys.map((obj) => {
        return obj.is_private
          ? { ...obj, is_private: "true" }
          : { ...obj, is_private: "false" };
      });
      setUserCollections(Array.isArray(updatedValues) ? updatedValues : []);
      setTableDataRows(updatedValues.slice(0, 5));
    } catch (error) {
      console.error("Error fetching user collections:", error);
      setErrorMessage(
        "Failed to fetch user collections. Please try again later."
      );
    } finally {
      // console.log(rendRows)
      setIsLoadingCollections(false);
    }
  };

  const createNewCollection = () => {
    navigate("/create-collection");
  };

  const onClickCollectionTable = (collectionId) => {
    setSelectedCollection(
      userCollections.find((collection) => collection.id === collectionId)
    );
  };

  /* TODO: fix bug with next page pagination component */
  const pageOnChange = (e) => {
    setTableDataRows(
      userCollections.slice((e.page - 1) * e.pageSize, e.page * e.pageSize)
    );
  };

  return (
    <Content className="view-content">
      <>
        <div className="view-title">
          <h2>Collections</h2>
          <Button
            renderIcon={Add}
            aria-label="Add new collection"
            onClick={() => createNewCollection()}
          >
            New Collection
          </Button>
        </div>

        {isLoadingCollections ? (
          <div className="data-loading">
            <Loading description="Loading collections" withOverlay={false} />
          </div>
        ) : (
          <>
            <DataTable rows={tableDataRows} headers={headers}>
              {({
                rows,
                headers,
                getTableProps,
                getHeaderProps,
                getRowProps,
                onInputChange,
              }) => (
                <>
                  <TableToolbar>
                    <div className="view-datatable-header">
                      Any header text about the data below...
                    </div>
                    <TableToolbarContent>
                      {/* pass in `onInputChange` change here to make filtering work */}
                      <TableToolbarSearch onChange={onInputChange} />
                      <TableToolbarMenu>
                        <TableToolbarAction onClick={() => {}}>
                          Action 1
                        </TableToolbarAction>
                        <TableToolbarAction onClick={() => {}}>
                          Action 2
                        </TableToolbarAction>
                        <TableToolbarAction onClick={() => {}}>
                          Action 3
                        </TableToolbarAction>
                      </TableToolbarMenu>
                    </TableToolbarContent>
                  </TableToolbar>

                  <Table {...getTableProps()}>
                    <TableHead key="table-head">
                      <TableRow>
                        {headers.map((header, idx) => (
                          <TableHeader
                            {...getHeaderProps({ header, isSortable: true })}
                            key={idx}
                          >
                            {header.header}
                          </TableHeader>
                        ))}
                        <TableHeader
                          key="column-menu-header"
                          className="view-tabledata-action"
                        ></TableHeader>
                      </TableRow>
                    </TableHead>
                    <TableBody key="table-body">
                      {rows.map((row, idx) => (
                        <TableRow
                          {...getRowProps({ row })}
                          key={idx}
                          onClick={() => onClickCollectionTable(row.id)}
                        >
                          {row.cells.map((cell) => (
                            <>
                              <TableCell key={cell.id}>{cell.value}</TableCell>
                            </>
                          ))}
                          <TableCell
                            key="column-menu"
                            className="cds--table-column-menu"
                          >
                            <OverflowMenu
                              size="sm"
                              flipped
                              aria-label="options 1"
                            >
                              <OverflowMenuItem
                                key="item-1"
                                itemText="View Collection"
                              />
                              <OverflowMenuItem
                                key="item-2"
                                itemText="Edit Collection"
                              />
                              <OverflowMenuItem
                                key="item-3"
                                itemText="Delete Collection"
                              />
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
              totalItems={userCollections.length}
              pageSize="5"
              onChange={(e) => pageOnChange(e)}
              pageSizes={[5, 10, 20, 50]}
              size="md"
            />
          </>
        )}
      </>
      <FlexGrid className="view-detail-grid">
        <Row>
          <Column>
            <div className="view-detail-label">Name:</div>
            <div className="view-detail-text">{selectedCollection?.name}</div>
          </Column>
          <Column>
            <div className="view-detail-label">ID:</div>
            <div className="view-detail-text">
              {selectedCollection?.collection_id}
            </div>
          </Column>
        </Row>
        <Row>
          <Column>
            <div className="view-detail-label">Private:</div>
            <div className="view-detail-text">
              {selectedCollection?.is_private ? "True" : "False"}
            </div>
          </Column>
          <Column>
            <div className="view-detail-label">Status</div>
            <div className="view-detail-text">{selectedCollection?.status}</div>
          </Column>
        </Row>

        <Row>
          <Column>
            <div className="view-detail-label">Created At:</div>
            <div className="view-detail-text">
              {selectedCollection?.created_at}
            </div>
          </Column>
          <Column>
            <div className="view-detail-label">Updated At:</div>
            <div className="view-detail-text">
              {selectedCollection?.updated_at}
            </div>
          </Column>
        </Row>
        <Row>
          <Column>
            <div className="view-detail-label">Files:</div>
            <div className="view-detail-text">
              <UnorderedList>
                {selectedCollection?.files?.map((file, idx) => {
                  return <ListItem key={idx}>{file.filename}</ListItem>;
                })}
              </UnorderedList>
            </div>
          </Column>
        </Row>
      </FlexGrid>
    </Content>
  );
};

export default Collections;
