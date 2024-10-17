import React, { useState, useEffect } from 'react';
import {
  TextInput,
  Button,
  Form,
  ToastNotification,

  InlineLoading,

} from '@carbon/react';
import { TrashCan, Document } from '@carbon/icons-react';

import { createAssistant, getAssistants } from 'src/api/collection_api';
import { useAuth } from 'src/contexts/AuthContext';
import { TextArea } from 'carbon-components-react';

const AssistantForm = () => {
  const { user, loading: authLoading } = useAuth();
  const [assistantName, setAssistantName] = useState('');
  const [files, setFiles] = useState([]);
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [showSuccessToast, setShowSuccessToast] = useState(false);
  const [assistants, setAssistants] = useState([]);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
   
  }, [user]);


  const handleSubmit = async (e) => {
    
  };

  return (
    <div className="children-container assistant-form">
      <h3>Your Assistants</h3>
      

      <h4>Run a Query</h4>
      <Form className="assistant-form" onSubmit={handleSubmit}>
        <TextInput
          id="query-input"
          labelText="Query"
          value={assistantName}
          onChange={(e) => setAssistantName(e.target.value)}
          disabled={isUploading}
        />
        <TextArea
          id="response-input"
          labelText="Response">

          </TextArea>

        <Button type="submit" kind="primary"> "Create Assistant"
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
          title="Save Assistant"
          subtitle="The files are being indexed in the vector DB, please check back later."
          caption=""
          timeout={5000}
          onClose={() => setShowSuccessToast(false)}
        />
      )}
    </div>
  );
};

export default AssistantForm;