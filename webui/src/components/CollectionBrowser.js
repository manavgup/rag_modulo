import React, { useState, useEffect } from 'react';
import {
  DataTable,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableHeader,
  TableBody,
  TableCell,
  Pagination,
  Search,
  Button,
  Modal,
  TextInput,
  FileUploader,
  Dropdown,
  InlineLoading,
  ComposedModal,
  ModalHeader,
  ModalBody,
  ModalFooter
} from 'carbon-components-react';
import { Add, TrashCan, Document} from '@carbon/icons-react';
import { getUserCollections, createCollectionWithDocuments, updateCollection, deleteCollection, getDocumentsInCollection, deleteDocument, moveDocument } from '../api/api';
import { useNotification } from '../contexts/NotificationContext';
import './CollectionBrowser.css';

const CollectionBrowser = () => {
  const [collections, setCollections] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('create');
  const [selectedCollection, setSelectedCollection] = useState(null);
  const [collectionName, setCollectionName] = useState('');
  const [collectionDescription, setCollectionDescription] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState(null);
  const [isMoveModalOpen, setIsMoveModalOpen] = useState(false);
  const [documentToMove, setDocumentToMove] = useState(null);
  const [targetCollection, setTargetCollection] = useState(null);
  const [sortField, setSortField] = useState('name');
  const [sortDirection, setSortDirection] = useState('asc');
  const { addNotification } = useNotification();

  useEffect(() => {
    fetchCollections();
  }, [currentPage, pageSize, searchTerm, sortField, sortDirection]);

  const fetchCollections = async () => {
    setIsLoading(true);
    try {
      const response = await getUserCollections(currentPage, pageSize, searchTerm, sortField, sortDirection);
      setCollections(response.data);
      setTotalItems(response.totalItems);
    } catch (error) {
      console.error('Error fetching collections:', error);
      addNotification('error', 'Error', 'Failed to fetch collections. Please try again.');
    }
    setIsLoading(false);
  };

  const handleCreateCollection = async () => {
    try {
      const formData = new FormData();
      formData.append('name', collectionName);
      formData.append('description', collectionDescription);
      uploadedFiles.forEach((file) => {
        formData.append('documents', file);
      });
      await createCollectionWithDocuments(formData);
      addNotification('success', 'Success', 'Collection created successfully.');
      fetchCollections();
      setIsModalOpen(false);
      resetModalFields();
    } catch (error) {
      console.error('Error creating collection:', error);
      addNotification('error', 'Error', 'Failed to create collection. Please try again.');
    }
  };

  const handleUpdateCollection = async () => {
    try {
      await updateCollection(selectedCollection.id, { name: collectionName, description: collectionDescription });
      addNotification('success', 'Success', 'Collection updated successfully.');
      fetchCollections();
      setIsModalOpen(false);
      resetModalFields();
    } catch (error) {
      console.error('Error updating collection:', error);
      addNotification('error', 'Error', 'Failed to update collection. Please try again.');
    }
  };

  const handleDeleteConfirm = async () => {
    try {
      if (itemToDelete.type === 'collection') {
        await deleteCollection(itemToDelete.id);
        addNotification('success', 'Success', 'Collection deleted successfully.');
        fetchCollections();
      } else if (itemToDelete.type === 'document') {
        await deleteDocument(selectedCollection.id, itemToDelete.id);
        addNotification('success', 'Success', 'Document deleted successfully.');
        fetchDocuments(selectedCollection.id);
      }
      setIsDeleteModalOpen(false);
      setItemToDelete(null);
    } catch (error) {
      console.error('Error deleting item:', error);
      addNotification('error', 'Error', 'Failed to delete item. Please try again.');
    }
  };

  const handleMoveDocument = async () => {
    try {
      await moveDocument(selectedCollection.id, documentToMove.id, targetCollection.id);
      addNotification('success', 'Success', 'Document moved successfully.');
      fetchDocuments(selectedCollection.id);
      setIsMoveModalOpen(false);
      setDocumentToMove(null);
      setTargetCollection(null);
    } catch (error) {
      console.error('Error moving document:', error);
      addNotification('error', 'Error', 'Failed to move document. Please try again.');
    }
  };

  const resetModalFields = () => {
    setCollectionName('');
    setCollectionDescription('');
    setUploadedFiles([]);
    setSelectedCollection(null);
  };

  const openCreateModal = () => {
    setModalMode('create');
    setIsModalOpen(true);
  };

  const openEditModal = (collection) => {
    setModalMode('edit');
    setSelectedCollection(collection);
    setCollectionName(collection.name);
    setCollectionDescription(collection.description);
    setIsModalOpen(true);
  };

  const openDeleteModal = (item, type) => {
    setItemToDelete({ ...item, type });
    setIsDeleteModalOpen(true);
  };

  const openMoveModal = (document) => {
    setDocumentToMove(document);
    setIsMoveModalOpen(true);
  };

  const fetchDocuments = async (collectionId) => {
    setIsLoading(true);
    try {
      const response = await getDocumentsInCollection(collectionId, currentPage, pageSize, searchTerm, sortField, sortDirection);
      setDocuments(response.data);
      setTotalItems(response.totalItems);
    } catch (error) {
      console.error('Error fetching documents:', error);
      addNotification('error', 'Error', 'Failed to fetch documents. Please try again.');
    }
    setIsLoading(false);
  };

  const handleSort = (field) => {
    if (field === sortField) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const collectionHeaders = [
    { key: 'name', header: 'Name' },
    { key: 'description', header: 'Description' },
    { key: 'documentCount', header: 'Documents' },
    { key: 'lastUpdated', header: 'Last Updated' },
    { key: 'actions', header: 'Actions' },
  ];

  const documentHeaders = [
    { key: 'name', header: 'Name' },
    { key: 'type', header: 'Type' },
    { key: 'size', header: 'Size' },
    { key: 'lastModified', header: 'Last Modified' },
    { key: 'actions', header: 'Actions' },
  ];

  const collectionRows = collections.map((collection) => ({
    id: collection.id,
    name: collection.name,
    description: collection.description,
    documentCount: collection.documentCount,
    lastUpdated: new Date(collection.lastUpdated).toLocaleDateString(),
    actions: (
      <>
        <Button
          kind="ghost"
          size="small"
          renderIcon={Document}
          iconDescription="View Documents"
          onClick={() => {
            setSelectedCollection(collection);
            fetchDocuments(collection.id);
          }}
        />
        <Button
          kind="ghost"
          size="small"
          renderIcon={Edit}
          iconDescription="Edit"
          onClick={() => openEditModal(collection)}
        />
        <Button
          kind="ghost"
          size="small"
          renderIcon={TrashCan}
          iconDescription="Delete"
          onClick={() => openDeleteModal(collection, 'collection')}
        />
      </>
    ),
  }));

  const documentRows = documents.map((document) => ({
    id: document.id,
    name: document.name,
    type: document.type,
    size: `${(document.size / 1024).toFixed(2)} KB`,
    lastModified: new Date(document.lastModified).toLocaleDateString(),
    actions: (
      <>
        <Button
          kind="ghost"
          size="small"
          renderIcon={TrashCan}
          iconDescription="Delete"
          onClick={() => openDeleteModal(document, 'document')}
        />
        <Button
          kind="ghost"
          size="small"
          renderIcon={Edit}
          iconDescription="Move"
          onClick={() => openMoveModal(document)}
        />
      </>
    ),
  }));

  return (
    <div className="collection-browser">
      <h1>{selectedCollection ? `Documents in ${selectedCollection.name}` : 'Document Collections'}</h1>
      <div className="collection-actions">
        <Search
          labelText="Search collections"
          placeholder="Enter collection name"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        {!selectedCollection && (
          <Button renderIcon={Add} onClick={openCreateModal}>
            Create Collection
          </Button>
        )}
        {selectedCollection && (
          <Button onClick={() => setSelectedCollection(null)}>
            Back to Collections
          </Button>
        )}
      </div>
      {isLoading ? (
        <InlineLoading description="Loading..." />
      ) : (
        <>
          <DataTable rows={selectedCollection ? documentRows : collectionRows} headers={selectedCollection ? documentHeaders : collectionHeaders}>
            {({ rows, headers, getHeaderProps, getTableProps }) => (
              <TableContainer>
                <Table {...getTableProps()}>
                  <TableHead>
                    <TableRow>
                      {headers.map((header) => (
                        <TableHeader {...getHeaderProps({ header })} onClick={() => handleSort(header.key)}>
                          {header.header}
                          {sortField === header.key && (
                            <span className="sort-indicator">{sortDirection === 'asc' ? '▲' : '▼'}</span>
                          )}
                        </TableHeader>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((row) => (
                      <TableRow key={row.id}>
                        {row.cells.map((cell) => (
                          <TableCell key={cell.id}>{cell.value}</TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </DataTable>
          <Pagination
            totalItems={totalItems}
            pageSize={pageSize}
            pageSizes={[10, 20, 30, 40, 50]}
            page={currentPage}
            onChange={({ page, pageSize }) => {
              setCurrentPage(page);
              setPageSize(pageSize);
            }}
          />
        </>
      )}
      <Modal
        open={isModalOpen}
        onRequestClose={() => {
          setIsModalOpen(false);
          resetModalFields();
        }}
        modalHeading={modalMode === 'create' ? 'Create Collection' : 'Edit Collection'}
        primaryButtonText={modalMode === 'create' ? 'Create' : 'Update'}
        secondaryButtonText="Cancel"
        onRequestSubmit={modalMode === 'create' ? handleCreateCollection : handleUpdateCollection}
      >
        <TextInput
          id="collection-name"
          labelText="Collection Name"
          value={collectionName}
          onChange={(e) => setCollectionName(e.target.value)}
          placeholder="Enter collection name"
          required
        />
        <TextInput
          id="collection-description"
          labelText="Description"
          value={collectionDescription}
          onChange={(e) => setCollectionDescription(e.target.value)}
          placeholder="Enter collection description"
        />
        {modalMode === 'create' && (
          <FileUploader
            labelTitle="Upload Documents"
            labelDescription="Max file size is 500mb. Only .pdf, .doc, .docx, and .txt files are supported."
            buttonLabel="Add files"
            filenameStatus="edit"
            accept={['.pdf', '.doc', '.docx', '.txt']}
            multiple
            onChange={(e) => setUploadedFiles(e.target.files)}
          />
        )}
      </Modal>
      <ComposedModal
        open={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
      >
        <ModalHeader title="Confirm Deletion" />
        <ModalBody>
          <p>Are you sure you want to delete this {itemToDelete?.type}? This action cannot be undone.</p>
        </ModalBody>
        <ModalFooter
          primaryButtonText="Delete"
          secondaryButtonText="Cancel"
          onRequestSubmit={handleDeleteConfirm}
          onRequestClose={() => setIsDeleteModalOpen(false)}
        />
      </ComposedModal>
      <ComposedModal
        open={isMoveModalOpen}
        onClose={() => setIsMoveModalOpen(false)}
      >
        <ModalHeader title="Move Document" />
        <ModalBody>
          <p>Select a collection to move the document to:</p>
          <Dropdown
            id="target-collection"
            titleText="Target Collection"
            items={collections.filter((c) => c.id !== selectedCollection.id)}
            itemToString={(item) => (item ? item.name : '')}
            onChange={({ selectedItem }) => setTargetCollection(selectedItem)}
          />
        </ModalBody>
        <ModalFooter
          primaryButtonText="Move"
          secondaryButtonText="Cancel"
          onRequestSubmit={handleMoveDocument}
          onRequestClose={() => setIsMoveModalOpen(false)}
        />
      </ComposedModal>
    </div>
  );
};

export default CollectionBrowser;