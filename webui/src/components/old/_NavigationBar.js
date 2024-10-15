import React from 'react';
import { Header, HeaderName, HeaderNavigation, HeaderMenuItem } from '@carbon/react';

const NavigationBar = () => (
  <Header aria-label="RAG Modulo">
    <HeaderName href="#" prefix="IBM">
      RAG Solution
    </HeaderName>
    <HeaderNavigation aria-label="">
      <HeaderMenuItem href="/">Home</HeaderMenuItem>
      <HeaderMenuItem href="/about">About</HeaderMenuItem>
    </HeaderNavigation>
  </Header>
);

export default NavigationBar;

