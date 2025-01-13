import React from 'react';
import './ConfigurationPage.css';
import {
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  Grid,
  Column
} from '@carbon/react';
import { Flow, Cloud, SettingsAdjust, Template } from '@carbon/icons-react';
import { useNavigate, useLocation } from 'react-router-dom';

import PipelineSettings from './PipelineSettings';
import LLMParameters from './LLMParameters';
import PromptTemplates from './PromptTemplates';
import ProviderSettings from './ProviderSettings';

const ConfigurationPage = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const getSelectedTab = () => {
    const path = location.pathname.split('/').pop();
    switch (path) {
      case 'providers':
        return 0;
      case 'pipeline':
        return 1;
      case 'llm':
        return 2;
      case 'templates':
        return 3;
      default:
        return 0;
    }
  };

  const handleTabChange = (index) => {
    switch (index) {
      case 0:
        navigate('/configuration/providers');
        break;
      case 1:
        navigate('/configuration/pipeline');
        break;
      case 2:
        navigate('/configuration/llm');
        break;
      case 3:
        navigate('/configuration/templates');
        break;
      default:
        navigate('/configuration/providers');
    }
  };

  return (
    <div className="configuration-page">
      <Grid>
        <Column lg={16} md={8} sm={4}>
          <h1>Configuration Management</h1>
          
          <Tabs selectedIndex={getSelectedTab()} onChange={handleTabChange}>
            <TabList aria-label="Configuration tabs">
              <Tab renderIcon={() => <Cloud size={16} />}>Provider Settings</Tab>
              <Tab renderIcon={() => <Flow size={16} />}>Pipeline Settings</Tab>
              <Tab renderIcon={() => <SettingsAdjust size={16} />}>LLM Parameters</Tab>
              <Tab renderIcon={() => <Template size={16} />}>Prompt Templates</Tab>
            </TabList>
            
            <TabPanels>
              <TabPanel>
                <div className="configuration-section">
                  <h2>Provider Settings</h2>
                  <p className="configuration-description">
                    Configure LLM providers with API keys and connection settings.
                  </p>
                  <ProviderSettings />
                </div>
              </TabPanel>
              
              <TabPanel>
                <div className="configuration-section">
                  <h2>Pipeline Settings</h2>
                  <p className="configuration-description">
                    Configure RAG pipelines with retrieval, reranking, and generation settings.
                  </p>
                  <PipelineSettings />
                </div>
              </TabPanel>
              
              <TabPanel>
                <div className="configuration-section">
                  <h2>LLM Parameters</h2>
                  <p className="configuration-description">
                    Manage model-specific parameters like temperature and token limits.
                  </p>
                  <LLMParameters />
                </div>
              </TabPanel>
              
              <TabPanel>
                <div className="configuration-section">
                  <h2>Prompt Templates</h2>
                  <p className="configuration-description">
                    Create and manage prompt templates with variables and formatting.
                  </p>
                  <PromptTemplates />
                </div>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </Column>
      </Grid>
    </div>
  );
};

export default ConfigurationPage;
