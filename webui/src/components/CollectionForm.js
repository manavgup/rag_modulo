import React, { useState, useEffect } from 'react';
import {
  TextInput,
  Button,
  Checkbox,
  FileUploaderDropContainer,
  FormItem,
  Form,
  Tag,
  ProgressBar,
  ToastNotification,
  Tile,
  Loading,
  InlineLoading,
  Grid,
  Column
} from '@carbon/react';
import { TrashCan, Document } from '@carbon/icons-react';
import { createCollectionWithDocuments, getUserCollections } from '../api/api';
import { useAuth } from '../contexts/AuthContext';

const CollectionForm = () => {
  const { user, loading: authLoading } = useAuth();
  const [collectionName, setCollectionName] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const [files, setFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [showSuccessToast, setShowSuccessToast] = useState(false);
  const [userCollections, setUserCollections] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingCollections, setIsLoadingCollections] = useState(false);

  useEffect(() => {
    if (user && user.uuid) {
      fetchUserCollections();
    }
  }, [user]);

  const fetchUserCollections = async () => {
    setIsLoadingCollections(true);
    try {
      const collectionsData = await getUserCollections(1, 10); // Add default page and pageSize
      setUserCollections(Array.isArray(collectionsData.collections) ? collectionsData.collections : []);
    } catch (error) {
      console.error('Error fetching user collections:', error);
      setErrorMessage('Failed to fetch user collections. Please try again later.');
      setShowError(true);
    } finally {
      setIsLoadingCollections(false);
    }
  };

  const handleFileDrop = (event) => {
    const newFiles = Array.from(event.target.files || []);
    const filteredFiles = newFiles.filter((file) => {
      const fileType = file.type.toLowerCase();
      return (
        fileType === 'application/pdf' ||
        fileType === 'application/vnd.ms-powerpoint' ||
        fileType === 'text/plain' ||
        fileType === 'application/msword' ||
        fileType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
        fileType === 'application/vnd.ms-excel' ||
        fileType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      );
    });

    if (filteredFiles.length !== newFiles.length) {
      setErrorMessage('Only PDF, PPT, Text, Word, and Excel files are allowed.');
      setShowError(true);
    } else {
      setShowError(false);
    }

    setFiles((prevFiles) => [...prevFiles, ...filteredFiles]);
  };

  const handleFileRemove = (index) => {
    setFiles((prevFiles) => prevFiles.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!user) {
      console.error("User not authenticated");
      setErrorMessage('User not authenticated. Please sign in.');
      setShowError(true);
      return;
    }

    if (files.length === 0) {
      setErrorMessage('Please add at least one file to the collection.');
      setShowError(true);
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append('collection_name', collectionName);
    formData.append('is_private', isPrivate);
    formData.append('user_id', user.uuid);

    files.forEach((file) => {
      formData.append('files', file);
    });

    try {
      const response = await createCollectionWithDocuments(formData, (event) => {
        const percentCompleted = Math.round((event.loaded * 100) / event.total);
        setUploadProgress(percentCompleted);
      });
      console.log('API Response:', response);
      setShowSuccessToast(true);
      await fetchUserCollections();
      // Reset form
      setCollectionName('');
      setIsPrivate(false);
      setFiles([]);
      setUploadProgress(0);
    } catch (error) {
      console.error('API Error:', error);
      setShowError(true);
      setErrorMessage(error.message || 'An error occurred while creating the collection.');
    } finally {
      setIsUploading(false);
    }
  };

  if (authLoading) {
    return <Loading description="Loading user data" withOverlay={false} />;
  }

  if (!user) {
    return (
      <div className="collection-form-container">
        <h2>Sign In Required</h2>
        <p>Please sign in to view and create collections.</p>
        <Button onClick={() => window.location.href = '/signin'}>Sign In</Button>
      </div>
    );
  }

  return (
    <div className="collection-form-container">
      <h2>Your Collections</h2>
      {isLoadingCollections ? (
        <Loading description="Loading collections" withOverlay={false} />
      ) : userCollections.length > 0 ? (
        <Grid narrow className="collections-grid">
          {userCollections.map((collection) => (
            <Column sm={4} md={4} lg={4} key={collection.id}>
              <Tile className="collection-tile">
                <h3>{collection.name}</h3>
                <p>
                  <Document size={16} /> Files: {collection.document_count || 'N/A'}
                </p>
                <p>Created: {new Date(collection.created_at).toLocaleDateString()}</p>
              </Tile>
            </Column>
          ))}
        </Grid>
      ) : (
        <p>No collections found. Create your first collection below!</p>
      )}

      <h2>Create New Collection</h2>
      <Form className="collection-form" onSubmit={handleSubmit}>
        <TextInput
          id="collection-name"
          labelText="Collection Name"
          value={collectionName}
          onChange={(e) => setCollectionName(e.target.value)}
          disabled={isUploading}
        />
        <Checkbox
          checked={isPrivate}
          labelText="Private Collection"
          id="private-collection-checkbox"
          onChange={(e) => setIsPrivate(e.target.checked)}
          disabled={isUploading}
        />
        <FormItem>
          <p className="cds--file--label">Upload files</p>
          <p className="cds--label-description">Max file size is 5MB. Supported formats: PDF, PPT, TXT, DOC, DOCX, XLS, XLSX</p>
          <FileUploaderDropContainer
            accept={[
              'application/pdf',
              'application/vnd.ms-powerpoint',
              'application/vnd.openxmlformats-officedocument.presentationml.presentation',
              'text/plain',
              'application/msword',
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
              'application/vnd.ms-excel',
              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ]}
            labelText="Drag and drop files here or click to upload"
            multiple
            onAddFiles={handleFileDrop}
            disabled={isUploading}
          />
          {files.length > 0 && (
            <div className="selected-files">
              <p>Selected Files:</p>
              {files.map((file, index) => (
                <div key={index} className="file-tag">
                  <Tag type="blue">{file.name}</Tag>
                  <Button
                    kind="ghost"
                    size="sm"
                    hasIconOnly
                    renderIcon={TrashCan}
                    iconDescription="Remove file"
                    onClick={() => handleFileRemove(index)}
                    disabled={isUploading}
                  />
                </div>
              ))}
            </div>
          )}
        </FormItem>

        {uploadProgress > 0 && (
          <ProgressBar
            label="Uploading..."
            value={uploadProgress}
          />
        )}

        <Button type="submit" kind="primary" disabled={isUploading || files.length === 0 || !collectionName}>
          {isUploading ? <InlineLoading description="Creating collection..." /> : "Create Collection"}
        </Button>
      </Form>

      {showError && (
        <ToastNotification
          kind="error"
          title="Error"
          subtitle={errorMessage}
          caption=""
          timeout={5000}
          onClose={() => setShowError(false)}
        />
      )}

      {showSuccessToast && (
        <ToastNotification
          kind="success"
          title="Collection Created"
          subtitle="The files are being indexed in the vector DB, please check back later."
          caption=""
          timeout={5000}
          onClose={() => setShowSuccessToast(false)}
        />
      )}
    </div>
  );
};

export default CollectionForm;