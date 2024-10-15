import React, { useState, useEffect } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import {
  Breadcrumb,
  BreadcrumbItem,
  Button,
  Loading,
  Tag,
  Tabs,
  Tab,
  TextInput,
  Modal,
  InlineNotification,
  StructuredListWrapper,
  StructuredListHead,
  StructuredListBody,
  StructuredListRow,
  StructuredListCell
} from 'carbon-components-react';
import { Document, Page } from 'react-pdf';
import { Download, Edit } from '@carbon/icons-react';
import { getDocument } from 'src/api/api';  // Removed updateDocumentMetadata import
import { useNotification } from 'src/contexts/NotificationContext';
import './DocumentViewer.css';

const DocumentViewer = () => {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [document, setDocument] = useState(null);
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editableMetadata, setEditableMetadata] = useState({});
  const [error, setError] = useState(null);
  const { addNotification } = useNotification();

  useEffect(() => {
    fetchDocument();
    if (location.state && location.state.searchTerm) {
      setSearchTerm(location.state.searchTerm);
    }
  }, [id, location]);

  const fetchDocument = async () => {
    setLoading(true);
    try {
      const response = await getDocument(id);
      setDocument(response.data);
      setEditableMetadata({
        title: response.data.title,
        author: response.data.author,
        description: response.data.description
      });
    } catch (error) {
      console.error('Error fetching document:', error);
      setError('Failed to load document. Please try again later.');
      addNotification('error', 'Error', 'Failed to load document. Please try again later.');
    }
    setLoading(false);
  };

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

  const handlePreviousPage = () => {
    setPageNumber((prevPageNumber) => Math.max(prevPageNumber - 1, 1));
  };

  const handleNextPage = () => {
    setPageNumber((prevPageNumber) => Math.min(prevPageNumber + 1, numPages));
  };

  const highlightSearchTerm = (text) => {
    if (!searchTerm) return text;
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    return text.split(regex).map((part, index) => 
      regex.test(part) ? <mark key={index}>{part}</mark> : part
    );
  };

  const handleDownload = () => {
    // Implement download functionality
    console.log('Downloading document:', document.id);
    addNotification('info', 'Download Started', 'Your document download has begun.');
  };

  const handleEditMetadata = async () => {
    try {
      // If the update functionality is needed, handle it here
      setDocument({ ...document, ...editableMetadata });
      setIsEditModalOpen(false);
      addNotification('success', 'Success', 'Document metadata updated successfully.');
    } catch (error) {
      console.error('Error updating metadata:', error);
      addNotification('error', 'Error', 'Failed to update metadata. Please try again.');
    }
  };

  const renderContent = () => {
    switch (document.type) {
      case 'pdf':
        return (
          <Document file={document.fileUrl} onLoadSuccess={onDocumentLoadSuccess}>
            <Page pageNumber={pageNumber} />
          </Document>
        );
      case 'txt':
      case 'docx':
        return (
          <div className="text-content">
            {highlightSearchTerm(document.content)}
          </div>
        );
      default:
        return <p>Unsupported file type</p>;
    }
  };

  if (loading) {
    return <Loading description="Loading document" />;
  }

  if (!document) {
    return <p>No document found</p>;
  }

  return (
    <div className="children-container document-viewer">
      <Breadcrumb>
        <BreadcrumbItem href="/">Home</BreadcrumbItem>
        <BreadcrumbItem href="/collections">Collections</BreadcrumbItem>
        <BreadcrumbItem href={`/collections/${document.collectionId}`}>
          {document.collectionName}
        </BreadcrumbItem>
        <BreadcrumbItem isCurrentPage>{document.title}</BreadcrumbItem>
      </Breadcrumb>

      <div className="document-header">
        <h3>{document.title}</h3>
        
        <div className="document-actions">
          <Button
            kind="ghost"
            renderIcon={Download}
            onClick={handleDownload}
          >
            Download
          </Button>
          <Button
            kind="ghost"
            renderIcon={Edit}
            onClick={() => setIsEditModalOpen(true)}
          >
            Edit Metadata
          </Button>
        </div>
      </div>
      
      {error && (
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={error}
          onClose={() => setError(null)}
        />
      )}

      <div className="document-metadata">
        <p>Author: {document.author}</p>
        <p>Date: {new Date(document.date).toLocaleDateString()}</p>
        <p>Type: {document.type}</p>
        {document.tags && document.tags.map((tag, index) => (
          <Tag key={index} type="blue">
            {tag}
          </Tag>
        ))}
      </div>

      <Tabs>
        <Tab id="document-content" label="Document Content">
          <div className="document-content">
            {renderContent()}
            {document.type === 'pdf' && (
              <div className="document-navigation">
                <Button onClick={handlePreviousPage} disabled={pageNumber <= 1}>
                  Previous
                </Button>
                <span>
                  Page {pageNumber} of {numPages}
                </span>
                <Button onClick={handleNextPage} disabled={pageNumber >= numPages}>
                  Next
                </Button>
              </div>
            )}
          </div>
        </Tab>
        <Tab id="document-metadata" label="Metadata">
          <div className="document-full-metadata">
            {Object.entries(document.metadata || {}).map(([key, value]) => (
              <p key={key}><strong>{key}:</strong> {value}</p>
            ))}
          </div>
        </Tab>
      </Tabs>

      <Modal
        open={isEditModalOpen}
        onRequestClose={() => setIsEditModalOpen(false)}
        modalHeading="Edit Document Metadata"
        primaryButtonText="Save"
        secondaryButtonText="Cancel"
        onRequestSubmit={handleEditMetadata}
      >
        <TextInput
          id="edit-title"
          labelText="Title"
          value={editableMetadata.title}
          onChange={(e) => setEditableMetadata({ ...editableMetadata, title: e.target.value })}
        />
        <TextInput
          id="edit-author"
          labelText="Author"
          value={editableMetadata.author}
          onChange={(e) => setEditableMetadata({ ...editableMetadata, author: e.target.value })}
        />
        <TextInput
          id="edit-description"
          labelText="Description"
          value={editableMetadata.description}
          onChange={(e) => setEditableMetadata({ ...editableMetadata, description: e.target.value })}
        />
      </Modal>
    </div>
  );
};

export default DocumentViewer;
