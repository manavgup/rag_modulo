import React, { useState } from 'react';
import axios from 'axios';
import {
  Form,
  TextInput,
  RadioButtonGroup,
  RadioButton,
  FileUploader,
  Button
} from '@carbon/react';

const CollectionForm = () => {
  const [collectionName, setCollectionName] = useState('');
  const [privacy, setPrivacy] = useState(false);
  const [files, setFiles] = useState([]);

  const handleFileChange = (event) => {
    setFiles(event.target.files);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const formData = new FormData();
    formData.append('name', collectionName);
    formData.append('privacy', privacy);
    Array.from(files).forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await axios.post('http://localhost:8000/collections/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      console.log(response.data);
    } catch (error) {
      console.error('There was an error creating the collection!', error);
    }
  };

  return (
    <Form onSubmit={handleSubmit}>
      <TextInput
        id="collection-name"
        labelText="Collection Name"
        value={collectionName}
        onChange={(e) => setCollectionName(e.target.value)}
      />
      <RadioButtonGroup
        legendText="Collection Privacy"
        name="privacy"
        onChange={(value) => setPrivacy(value === 'private')}
      >
        <RadioButton id="public" labelText="Public" value="public" />
        <RadioButton id="private" labelText="Private" value="private" />
      </RadioButtonGroup>
      <FileUploader
        labelTitle="Add files"
        multiple
        onChange={handleFileChange}
      />
      <Button type="submit">Create Collection</Button>
    </Form>
  );
};

export default CollectionForm;
