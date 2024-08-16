import React, { useState, useEffect } from 'react';
import { TextInput, Button, Checkbox, FileUploaderDropContainer, FormItem, Form, Tag, ProgressBar, ToastNotification } from '@carbon/react';
import { TrashCan  } from '@carbon/icons-react';
import { createCollectionWithDocuments } from '../api/api';

const CollectionForm = ({ onSubmit }) => {
  const [collectionName, setCollectionName] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const [files, setFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);

  useEffect(() => {
    if (typeof File === 'undefined') {
      console.error('File API is not supported in this browser.');
    }
  }, []);

  const handleFileDrop = (event) => {
    console.log("handleFileDrop: ", event);
    const newFiles = Array.from(event.target.files || []);
    console.log("handleFileDrop newFiles: ", newFiles);
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

    console.log("filteredFiles Length: ", filteredFiles.length, ": newFiles Length: ", newFiles.length);

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

    console.log('Files:', files);

    const formData = new FormData();
    formData.append('collection_name', collectionName);
    formData.append('is_private', isPrivate);

    files.forEach((file) => {
      formData.append('files', file);
    });

    try {
      const response = await createCollectionWithDocuments(formData, (event) => {
        const percentCompleted = Math.round((event.loaded * 100) / event.total);
        setUploadProgress(percentCompleted);
      });
      console.log('API Response:', response);
      setIsSubmitted(true);
      onSubmit(response);
    } catch (error) {
      console.log('API Error:', error);
      setShowError(true);
      setErrorMessage(error.response?.data?.message || 'An error occurred.');
    }
  };

  if (isSubmitted) {
    return (
      <div>
        <h2>Collection Created</h2>
        <p>The files are being indexed in the vector DB, please check back later.</p>
      </div>
    );
  }

  return (
    <Form className="collection-form" onSubmit={handleSubmit}>
      <TextInput
        id="collection-name"
        labelText="Collection Name"
        value={collectionName}
        onChange={(e) => setCollectionName(e.target.value)}
      />
      <Checkbox
        className="cds--label-description"
        defaultChecked={isPrivate}
        labelText="Private Collection?"
        id="checkbox-label-1"
        onChange={(e) => setIsPrivate(e.target.checked)}
      />
      <FormItem>
        <p className="cds--file--label"> Upload files </p>
        <p className="cds--label-description"> Max file size is 5MB.</p>
        <FileUploaderDropContainer
          accept={[
            'text/plain',
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.ms-excel',
          ]}
          labelText="Drag and drop files here or click to upload"
          multiple
          onAddFiles={handleFileDrop}
        />
        {files.length > 0 && (
          <div className="selected-files">
            <p>Selected Files:</p>
            {files.map((file, index) => (
              <div key={index} style={{ display: 'flex', alignItems: 'center' }}>
                <Tag type="gray">{file.name}</Tag>
                <Button
                  kind="primary"
                  size="sm"
                  hasIconOnly
                  renderIcon={ TrashCan }
                  iconDescription="Remove file"
                  tooltipPosition="right"
                  onClick={() => handleFileRemove(index)}
                  style={{ marginLeft: '0.5rem' }}
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

      <ToastNotification
        kind="error"
        title="Error"
        subtitle={errorMessage}
        caption=""
        timeout={5000}
        onClose={() => setShowError(false)}
        style={{ display: showError ? 'block' : 'none' }}
      />

      <Button type="submit" kind="primary">
        Create Collection
      </Button>
    </Form>
  );
};

export default CollectionForm;
