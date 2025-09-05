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
  UnorderedList,
  ListItem,
  Pagination,
  IconButton,
  Tile,
  FileUploader,
  TextInput,
  ProgressBar,
  Checkbox,
  ComposedModal,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from "@carbon/react";
import { Add, AddFilled, Chat, Document, TrashCan } from "@carbon/icons-react";
import {
  DataTable as IconDataTable,
  Grid as IconGrid,
} from "@carbon/icons-react";

import {
  getUserCollections,
  createCollectionWithDocuments,
  updateCollection,
  deleteCollection,
  getDocumentsInCollection,
  deleteDocument,
  moveDocument,
} from "src/api/api";

import "./Collection.css";
import "src/styles/view-ui.css";
import { Modal } from "@carbon/react";
import { useAuth } from "src/contexts/AuthContext";

const Collections = () => {
  /* TODO: Add a messageQueue for the application */
  const { user } = useAuth();
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoadingCollections, setIsLoadingCollections] = useState(false);
  const [userCollections, setUserCollections] = useState([]);
  const [tableDataRows, setTableDataRows] = useState([]);
  const [selectedCollection, setSelectedCollection] = useState([]);
  const [tableView, setTableView] = useState(false);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState("create");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  const [collectionData, setCollectionData] = useState({
    name: "",
    description: "",
    is_private: false,
    files: [],
  });
  const [itemToDelete, setItemToDelete] = useState(null);

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

  const handleLayoutViewChange = () => {
    setTableView(!tableView);
  };

  const resetModalFields = () => {
    setCollectionData({
      name: "",
      description: "",
      is_private: false,
      files: [],
    });
    setIsModalOpen(false);
  };

  const openDeleteModal = (item, type) => {
    setItemToDelete({ ...item, type });
    setIsDeleteModalOpen(true);
  };

  const handleDeleteConfirm = async () => {
    try {
      if (itemToDelete.type === "collection") {
        await deleteCollection(itemToDelete.id);
       fetchUserCollections();
      } else if (itemToDelete.type === "document") {
        await deleteDocument(selectedCollection.id, itemToDelete.id);
      }
      setIsDeleteModalOpen(false);
      setItemToDelete(null);
    } catch (error) {
      console.error("Error deleting item:", error);
    }
  };


  const fetchUserCollections = async () => {
    setIsLoadingCollections(true);
    try {
      const collections = (await getUserCollections())?.collections;

      if (collections && collections.length > 0) {
        // data table requires a field called id
        const updatedKeys = collections.map(
          ({ collection_id: id, ...rest }) => ({
            id,
            ...rest,
          })
        );

        setUserCollections(updatedKeys);
        setTableDataRows(updatedKeys.slice(0, 5));
      } else {
        setUserCollections([]);
        setTableDataRows([]);
      }
    } catch (error) {
      console.error("Error fetching user collections:", error);
      setErrorMessage(
        "Failed to fetch user collections. Please try again later."
      );
    } finally {
      setIsLoadingCollections(false);
    }
  };

  const createNewCollection = () => {
    setModalMode("create");
    setIsModalOpen(true);
  };

  const handleCreateCollection = async () => {
    try {
      const formData = new FormData();

      formData.append("collection_name", collectionData.name);
      formData.append("description", collectionData.description);
      formData.append("is_private", collectionData.is_private);
      Array.from(collectionData.files).forEach((file) => {
        formData.append("files", file);
      });
      formData.append("user_id", user.uuid);
      try {
        setIsUploading(true);
        const response = await createCollectionWithDocuments(
          formData,
          (event) => {
            const percentCompleted = Math.round(
              (event.loaded * 100) / event.total
            );
            setUploadProgress(percentCompleted);
          }
        );
        await fetchUserCollections();
        // Reset form
        setUploadProgress(0);

        fetchUserCollections();
        setIsModalOpen(false);
        resetModalFields();
      } catch (error) {
        setErrorMessage(
          error.message || "An error occurred while creating the collection."
        );
      } finally {
        setIsUploading(false);
      }
    } catch (error) {
      console.error("Error creating collection:", error);
    }
  };

  const handleUpdateCollection = async () => {

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
    <Content className="children-container  view-content">
      <>
        <div className="view-title">
          <h3>Collections</h3>
          <IconButton
            label="New"
            aria-label="Add new collection"
            onClick={() => createNewCollection()}
            kind="ghost"
          >
            <Add size={30} />
          </IconButton>
          <IconButton
            label="New"
            aria-label="Add new collection"
            onClick={() => handleLayoutViewChange()}
            kind="ghost"
          >
            {tableView ? <IconDataTable size={30} /> : <IconGrid size={30} />}
          </IconButton>
        </div>

        {isLoadingCollections ? (
          <div className="data-loading">
            <Loading description="Loading collections" withOverlay={false} />
          </div>
        ) : (
          <>
            {tableView ? (
              <Content className="collection-view-table">
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
                        {/* <div className="view-datatable-header">
                      Any header text about the data below...
                    </div> */}
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
                                {...getHeaderProps({
                                  header,
                                  isSortable: true,
                                })}
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
                                  <TableCell key={cell.id}>
                                    {typeof cell.value === "boolean"
                                      ? cell.value
                                        ? "Yes"
                                        : "No"
                                      : cell.value}
                                  </TableCell>
                                </>
                              ))}
                              <TableCell
                                key="column-menu"
                                className="cds--table-column-menu"
                              >
                                <IconButton
                                  label="Chat with collection"
                                  aria-label="Chat with collection"
                                  onClick={() =>
                                    onClickCollectionTable(row.id)
                                  }
                                  kind="ghost"
                                >
                                  <Chat size={16} />
                                </IconButton>
                                <IconButton
                                  label="Delete"
                                  aria-label="Delete"
                                  onClick={() => {openDeleteModal(row, "collection")}}
                                  kind="ghost"
                                >
                                  <TrashCan size={16} />
                                </IconButton>
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
                <FlexGrid className="view-detail-grid">
                  <Row>
                    <Column>
                      <div className="view-detail-label">Name:</div>
                      <div className="view-detail-text">
                        {selectedCollection?.name}
                      </div>
                    </Column>
                    <Column>
                      <div className="view-detail-label">ID:</div>
                      <div className="view-detail-text">
                        {selectedCollection?.id}
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
                      <div className="view-detail-text">
                        {selectedCollection?.status}
                      </div>
                    </Column>
                  </Row>

                  <Row>
                    <Column>
                      <div className="view-detail-label">Created At:</div>
                      <div className="view-detail-text">
                        {selectedCollection?.created_at &&
                          new Date(
                            selectedCollection?.created_at
                          ).toLocaleDateString()}
                      </div>
                    </Column>
                    <Column>
                      <div className="view-detail-label">Updated At:</div>
                      <div className="view-detail-text">
                        {selectedCollection?.updated_at &&
                          new Date(
                            selectedCollection?.updated_at
                          ).toLocaleDateString()}
                      </div>
                    </Column>
                  </Row>
                  <Row>
                    <Column>
                      <div className="view-detail-label">Files:</div>
                      <div className="view-detail-text collection-tile-content">
                        <UnorderedList>
                          {selectedCollection?.files?.map((file, idx) => {
                            return (
                              <ListItem key={file.id}>
                                <Document />{" "}
                                <span className="list-file-name">
                                  {file.filename}
                                </span>
                                <span className="list-file-size">500KB</span>
                              </ListItem>
                            );
                          })}
                        </UnorderedList>
                      </div>
                    </Column>
                  </Row>
                </FlexGrid>
              </Content>
            ) : (
              <>
                <Content className="collection-view-tile">
                  {userCollections.length > 0 &&
                    userCollections.map((collection) => (
                      <Tile key={collection.id} className="collection-tile">
                        <div className="collection-tile-header">
                          <h4 className="collection-tile-name">
                            {collection.name}
                          </h4>
                          <IconButton
                            label="Chat with collection"
                            aria-label="Chat with collection"
                            onClick={() => onClickCollectionTable(collection.id)}
                            kind="ghost"
                          >
                            <Chat size={20} />
                          </IconButton>
                          <IconButton
                            label="Delete collection"
                            aria-label="Delete collection"
                            onClick={() => {openDeleteModal(collection, "collection")}}
                            kind="ghost"
                          >
                            <TrashCan size={20} />
                          </IconButton>
                        </div>
                        <div className="collection-tile-content">
                          {collection?.files.length > 0 && (
                            <>
                              <UnorderedList kind="inline">
                                {collection.files.map((file) => (
                                  <ListItem key={file.id}>
                                    <Document />
                                    <span className="list-file-name">
                                      {file.filename}
                                    </span>
                                    <span className="list-file-size">
                                      500KB
                                    </span>
                                  </ListItem>
                                ))}
                              </UnorderedList>
                            </>
                          )}
                        </div>
                      </Tile>
                    ))}
                </Content>
              </>
            )}
          </>
        )}
      </>

      <Modal
        open={isModalOpen}
        onRequestClose={() => {
          setIsModalOpen(false);
          resetModalFields();
        }}
        modalHeading={
          modalMode === "create" ? "Create Collection" : "Edit Collection"
        }
        primaryButtonText={modalMode === "create" ? "Create" : "Update"}
        secondaryButtonText="Cancel"
        onRequestSubmit={() => {
          if (modalMode === "create") {
            handleCreateCollection();
          } else {
            handleUpdateCollection();
          }
        }}
      >
        <TextInput
          id="collection-name"
          labelText="Collection Name"
          value={collectionData.name}
          onChange={(e) =>
            setCollectionData({ ...collectionData, name: e.target.value })
          }
          placeholder="Enter collection name"
          required
        />
        <TextInput
          id="collection-description"
          labelText="Description"
          value={collectionData.description}
          onChange={(e) =>
            setCollectionData({
              ...collectionData,
              description: e.target.value,
            })
          }
          placeholder="Enter collection description"
        />

        <Checkbox
          checked={collectionData.is_private}
          labelText="Private Collection"
          id="private-collection-checkbox"
          onChange={(e) =>
            setCollectionData({
              ...collectionData,
              is_private: e.target.checked,
            })
          }
          disabled={isUploading}
        />
        {modalMode === "create" && (
          <FileUploader
            labelTitle="Upload Documents"
            labelDescription="Max file size is 500mb. Only .pdf, .doc, .docx, and .txt files are supported."
            buttonLabel="Add files"
            filenameStatus="edit"
            accept={[".pdf", ".doc", ".docx", ".txt"]}
            multiple
            value={collectionData.files}
            onChange={(e) =>
              setCollectionData({ ...collectionData, files: e.target.files })
            }
          />
        )}

        {uploadProgress > 0 && (
          <ProgressBar label="Uploading..." value={uploadProgress} />
        )}
      </Modal>

      <ComposedModal
        open={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
      >
        <ModalHeader title="Confirm Deletion" />
        <ModalBody>
          <p>
            Are you sure you want to delete this {itemToDelete?.type}? This
            action cannot be undone.
          </p>
        </ModalBody>
        <ModalFooter
          primaryButtonText="Delete"
          secondaryButtonText="Cancel"
          onRequestSubmit={handleDeleteConfirm}
          onRequestClose={() => setIsDeleteModalOpen(false)}
        />
      </ComposedModal>
    </Content>
  );
};

export default Collections;
